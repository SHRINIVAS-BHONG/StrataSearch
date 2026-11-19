"""
Database and Indexing layer for StrataSearch.

Provides:
- Thread-safe PostgreSQL connection pool with lazy initialization and graceful fallback.
- pgvector registration for vector similarity operations.
- Schema initialization with HNSW (cosine) and GIN (full-text search) index definitions.
- High-speed batch insertion using psycopg2.extras.execute_values.
"""

import logging
import math
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import psycopg2
import psycopg2.pool
import psycopg2.extras
from pgvector.psycopg2 import register_vector

from app.config import (
    DATABASE_URL,
    DB_POOL_MINCONN,
    DB_POOL_MAXCONN,
    SINGLE_NODE_MODE,
    MAX_UPLOAD_SIZE_BYTES,
)

logger = logging.getLogger(__name__)

# Global connection pool and lock for thread-safe singleton initialization
_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool(
    dsn: Optional[str] = None,
    minconn: Optional[int] = None,
    maxconn: Optional[int] = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> psycopg2.pool.ThreadedConnectionPool:
    """Lazily initializes and returns the thread-safe PostgreSQL connection pool.

    Args:
        dsn: Connection string (defaults to DATABASE_URL from config).
        minconn: Minimum pool connections (defaults to DB_POOL_MINCONN / 2).
        maxconn: Maximum pool connections (defaults to DB_POOL_MAXCONN / 20).
        max_retries: Number of connection attempts before raising OperationalError.
        retry_delay: Delay in seconds between retries during startup.

    Returns:
        psycopg2.pool.ThreadedConnectionPool: The active connection pool.
    """
    global _pool

    if _pool is not None and not _pool.closed:
        return _pool

    with _pool_lock:
        if _pool is not None and not _pool.closed:
            return _pool

        target_dsn = dsn or DATABASE_URL
        target_min = minconn if minconn is not None else DB_POOL_MINCONN
        target_max = maxconn if maxconn is not None else DB_POOL_MAXCONN

        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Initializing PostgreSQL connection pool (attempt {attempt}/{max_retries}) "
                    f"minconn={target_min}, maxconn={target_max}..."
                )
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=target_min,
                    maxconn=target_max,
                    dsn=target_dsn,
                )
                logger.info("PostgreSQL ThreadedConnectionPool successfully initialized.")
                return _pool
            except psycopg2.OperationalError as e:
                last_error = e
                logger.warning(
                    f"Database connection attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)

        raise psycopg2.OperationalError(
            f"Could not connect to PostgreSQL pool after {max_retries} attempts: {last_error}"
        )


def get_connection():
    """Fetches a connection from the pool and registers pgvector via register_vector(conn).

    Returns:
        psycopg2 connection object with pgvector registered.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        register_vector(conn)
    except Exception as e:
        # Non-fatal if vector extension is not yet created in the DB (e.g. before init_db() runs)
        logger.debug(f"pgvector registration note: {e}")
    return conn


def release_connection(conn) -> None:
    """Safely returns a connection back to the connection pool.

    Guarantees that uncommitted or errored transactions are rolled back
    so connections are never returned to the pool in 'idle in transaction'
    or 'idle in transaction (aborted)' states.

    Args:
        conn: The psycopg2 connection to return.
    """
    if conn is None:
        return
    try:
        # Check if connection is still open
        if not getattr(conn, "closed", False):
            try:
                idle_status = getattr(psycopg2.extensions, "TRANSACTION_STATUS_IDLE", 0)
                if hasattr(conn, "get_transaction_status"):
                    status = conn.get_transaction_status()
                    if status != idle_status:
                        conn.rollback()
            except Exception as tx_err:
                logger.warning(f"Error resetting transaction status on connection release: {tx_err}")
                try:
                    conn.close()
                except Exception:
                    pass

        pool = get_pool()
        if pool and not pool.closed:
            if getattr(conn, "closed", False):
                pool.putconn(conn, close=True)
            else:
                pool.putconn(conn)
        else:
            conn.close()
    except Exception as e:
        logger.warning(f"Error releasing connection back to pool: {e}")
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_db_connection():
    """Context manager for acquiring and safely releasing a database connection.

    Ensures rollback on error and guarantees connection release in all cases.
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        try:
            if not getattr(conn, "closed", False):
                conn.rollback()
        except Exception as rb_err:
            logger.warning(f"Error rolling back in get_db_connection: {rb_err}")
        raise
    finally:
        release_connection(conn)


def close_pool() -> None:
    """Closes all connections in the pool and resets pool instance."""
    global _pool
    with _pool_lock:
        if _pool is not None and not _pool.closed:
            _pool.closeall()
            _pool = None
            logger.info("PostgreSQL connection pool closed.")


def _format_embedding(emb: Any) -> Optional[str]:
    """Formats an embedding vector into PostgreSQL vector literal '[x,y,z]'.

    Validates that:
    - None returns None.
    - list or tuple of numeric values (floats/ints) are formatted to '[x,y,z]'.
    - 1D numpy ndarray (float32, float64, etc.) is formatted to '[x,y,z]'.
    - Valid pre-formatted string (e.g. '[0.1, 0.2]') is verified and returned.
    - Invalid types (dict, set, bool, non-numeric items, multi-dim arrays, invalid strings)
      raise ValueError or TypeError.

    Args:
        emb: Embedding input (list, tuple, numpy ndarray, valid vector string, or None).

    Returns:
        Optional[str]: Formatted string literal suitable for pgvector, or None.

    Raises:
        TypeError: If emb or any element is of an unsupported or non-numeric type.
        ValueError: If emb has invalid dimension, empty content, or malformed string syntax.
    """
    if emb is None:
        return None

    # Booleans are subclasses of int in Python; reject explicitly
    if isinstance(emb, bool):
        raise TypeError("Invalid embedding type bool; expected sequence of numbers or None.")

    # String format validation
    if isinstance(emb, str):
        s = emb.strip()
        if not (s.startswith("[") and s.endswith("]")):
            raise ValueError(
                f"Invalid pgvector string representation: must start with '[' and end with ']': {emb!r}"
            )
        inner = s[1:-1].strip()
        if not inner:
            raise ValueError("Empty vector string '[]' is not a valid embedding vector.")
        parts = [p.strip() for p in inner.split(",")]
        for p in parts:
            if not p:
                raise ValueError(f"Malformed vector string containing empty component: {emb!r}")
            try:
                val = float(p)
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Invalid numeric value in vector string (NaN/Inf): {p!r}")
            except ValueError as err:
                raise ValueError(f"Non-numeric component in vector string: {p!r}") from err
        return s

    # Numpy array or object with .ndim / .tolist
    if hasattr(emb, "ndim") and hasattr(emb, "tolist"):
        if emb.ndim != 1:
            raise ValueError(
                f"Embedding array must be 1-dimensional, got {emb.ndim}D array with shape {getattr(emb, 'shape', ())}"
            )
        if hasattr(emb, "dtype"):
            try:
                import numpy as np
                if not np.issubdtype(emb.dtype, np.number) or np.issubdtype(emb.dtype, np.bool_):
                    raise TypeError(f"Embedding array must have numeric dtype, got {emb.dtype}")
            except ImportError:
                pass
        emb_list = emb.tolist()
    elif isinstance(emb, (list, tuple)):
        emb_list = emb
    else:
        raise TypeError(
            f"Unsupported embedding type {type(emb).__name__}; expected list, numpy ndarray, valid vector string, or None."
        )

    if len(emb_list) == 0:
        raise ValueError("Embedding sequence cannot be empty.")

    formatted_items = []
    for idx, x in enumerate(emb_list):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            try:
                import numpy as np
                if not isinstance(x, np.number):
                    raise TypeError
                val = float(x)
            except Exception as err:
                raise TypeError(f"Non-numeric element at index {idx} ({type(x).__name__}): {x!r}") from err
        else:
            val = float(x)
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Invalid numeric value at index {idx}: NaN and Inf are not allowed in embeddings.")
        formatted_items.append(str(val))

    return "[" + ",".join(formatted_items) + "]"


def init_db(max_retries: int = 5, retry_delay: float = 2.0) -> None:
    """Initializes the database schema and indexes.

    Creates:
    - vector extension (CREATE EXTENSION IF NOT EXISTS vector)
    - documents metadata table:
        doc_id TEXT PRIMARY KEY
        filename TEXT NOT NULL
        source_type TEXT NOT NULL
        file_size_bytes BIGINT NOT NULL DEFAULT 0
        chunk_count INT NOT NULL DEFAULT 0
        status TEXT NOT NULL DEFAULT 'queued'
        error_message TEXT
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    - document_chunks table:
        id SERIAL PRIMARY KEY
        doc_id TEXT REFERENCES documents(doc_id) ON DELETE CASCADE
        source_id VARCHAR(255) NOT NULL
        chunk_index INTEGER NOT NULL
        content TEXT NOT NULL
        embedding vector(384)
        tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        CONSTRAINT uq_document_chunks_source_chunk UNIQUE (source_id, chunk_index)
    - HNSW vector index:
        USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
    - GIN full-text index on tsv
    - B-Tree index on source_id
    - B-Tree index on doc_id

    Args:
        max_retries: Number of retry attempts when database is starting up.
        retry_delay: Delay in seconds between retries.
    """
    logger.info("Starting database schema initialization...")
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                # 1. Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # Re-register pgvector now that extension is guaranteed to exist
                try:
                    register_vector(conn)
                except Exception as ex:
                    logger.debug(f"register_vector notice during init: {ex}")

                # 2. Create documents metadata table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        doc_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        file_size_bytes BIGINT NOT NULL DEFAULT 0,
                        chunk_count INT NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'queued',
                        error_message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 3. Create document_chunks table with doc_id foreign key cascade
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        doc_id TEXT REFERENCES documents(doc_id) ON DELETE CASCADE,
                        source_id VARCHAR(255) NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(384),
                        tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_document_chunks_source_chunk UNIQUE (source_id, chunk_index)
                    );
                """)

                # 4. Migrate pre-existing table: add doc_id column with FK cascade if not present
                cur.execute("""
                    ALTER TABLE document_chunks
                    ADD COLUMN IF NOT EXISTS doc_id TEXT REFERENCES documents(doc_id) ON DELETE CASCADE; -- CREATE TABLE migration
                """)

                # 5. Create unique index on (source_id, chunk_index) if table already existed without constraint
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_source_chunk
                    ON document_chunks (source_id, chunk_index);
                """)

                # 6. Create HNSW index on embedding for cosine distance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
                    ON document_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)

                # 7. Create GIN index on full-text tsvector
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_tsv_gin
                    ON document_chunks
                    USING gin (tsv);
                """)

                # 8. Create index on source_id for fast source lookups and filtering
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_source_id
                    ON document_chunks (source_id);
                """)

                # 9. Create B-Tree index on doc_id for fast document-scoped lookups and cascades
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id
                    ON document_chunks (doc_id);
                """)

            conn.commit()
            logger.info("Database schema, tables, and HNSW/GIN indexes successfully initialized.")
            return
        except psycopg2.OperationalError as e:
            last_error = e
            logger.warning(
                f"Database init attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {retry_delay}s..."
            )
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            time.sleep(retry_delay)
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            if conn:
                release_connection(conn)

    raise psycopg2.OperationalError(
        f"Database initialization failed after {max_retries} attempts: {last_error}"
    )


def insert_chunks_batch(
    chunks_or_source_id: Any = None,
    chunks: Optional[List[Any]] = None,
    embeddings: Optional[Sequence[Any]] = None,
    start_chunk_index: int = 0,
    doc_id: Optional[str] = None,
    source_id: Optional[str] = None,
) -> int:
    """Uses psycopg2.extras.execute_values for high-speed single-transaction batch insertion.

    Supports both calling conventions:
    1. Legacy parameter format:
       insert_chunks_batch(source_id, chunks, embeddings, start_chunk_index=0, doc_id=None)
    2. Document tuple list format:
       insert_chunks_batch(chunks=[(source_id, chunk_index, content, embedding), ...], doc_id=None)

    Args:
        chunks_or_source_id: Source ID string or list of chunk tuples.
        chunks: List of chunk text strings (or list of tuples if source_id is None).
        embeddings: List of embedding vectors (list of floats, numpy arrays, or tensors).
        start_chunk_index: Starting 0-based chunk index offset for batch insertion (default 0).
        doc_id: Optional document ID foreign key referencing documents(doc_id).
        source_id: Optional explicit source document identifier.

    Returns:
        int: Number of chunks successfully inserted.
    """
    target_doc_id = doc_id
    records: List[tuple] = []

    # Format 2: chunks_or_source_id is a list of chunk tuples
    if isinstance(chunks_or_source_id, (list, tuple)) and (chunks is None or isinstance(chunks, str)):
        if isinstance(chunks, str) and target_doc_id is None:
            target_doc_id = chunks
        tuple_list = chunks_or_source_id
        if not tuple_list:
            return 0
        for item in tuple_list:
            if isinstance(item, (list, tuple)):
                if len(item) == 5:
                    item_doc_id, item_src_id, item_idx, item_content, item_emb = item
                elif len(item) == 4:
                    item_src_id, item_idx, item_content, item_emb = item
                    item_doc_id = target_doc_id
                elif len(item) == 3:
                    item_idx, item_content, item_emb = item
                    item_src_id = source_id or target_doc_id or "unknown"
                    item_doc_id = target_doc_id
                else:
                    raise ValueError(f"Unexpected chunk tuple format with length {len(item)}: {item}")
            else:
                raise TypeError(f"Expected tuple/list chunk item, got {type(item).__name__}")

            formatted_emb = _format_embedding(item_emb)
            if item_doc_id is not None:
                records.append((item_doc_id, item_src_id, item_idx, item_content, formatted_emb))
            else:
                records.append((item_src_id, item_idx, item_content, formatted_emb))

    elif chunks_or_source_id is None and isinstance(chunks, (list, tuple)) and chunks and isinstance(chunks[0], (tuple, list)):
        for item in chunks:
            if len(item) == 5:
                item_doc_id, item_src_id, item_idx, item_content, item_emb = item
            elif len(item) == 4:
                item_src_id, item_idx, item_content, item_emb = item
                item_doc_id = target_doc_id
            elif len(item) == 3:
                item_idx, item_content, item_emb = item
                item_src_id = source_id or target_doc_id or "unknown"
                item_doc_id = target_doc_id
            else:
                raise ValueError(f"Unexpected chunk tuple format with length {len(item)}: {item}")
            formatted_emb = _format_embedding(item_emb)
            if item_doc_id is not None:
                records.append((item_doc_id, item_src_id, item_idx, item_content, formatted_emb))
            else:
                records.append((item_src_id, item_idx, item_content, formatted_emb))
    else:
        # Standard signature: (source_id, chunks, embeddings, start_chunk_index=0, doc_id=None)
        effective_source_id = source_id if source_id is not None else chunks_or_source_id
        if not isinstance(effective_source_id, str):
            effective_source_id = str(effective_source_id or "")

        chunks_list = chunks if chunks is not None else []
        embeddings_list = embeddings if embeddings is not None else []

        if len(chunks_list) != len(embeddings_list):
            raise ValueError(
                f"Mismatched batch sizes: {len(chunks_list)} chunks vs {len(embeddings_list)} embeddings."
            )

        if not chunks_list:
            return 0

        for idx, (chunk_text, emb) in enumerate(zip(chunks_list, embeddings_list), start=start_chunk_index):
            formatted_emb = _format_embedding(emb)
            if target_doc_id is not None:
                records.append((target_doc_id, effective_source_id, idx, chunk_text, formatted_emb))
            else:
                records.append((effective_source_id, idx, chunk_text, formatted_emb))

    if not records:
        return 0

    has_doc_id = any(len(r) == 5 for r in records)
    if has_doc_id:
        insert_sql = """
            INSERT INTO document_chunks (doc_id, source_id, chunk_index, content, embedding)
            VALUES %s
            ON CONFLICT (source_id, chunk_index)
            DO UPDATE SET
                doc_id = EXCLUDED.doc_id,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding
        """
        template = "(%s, %s, %s, %s, %s::vector)"
    else:
        insert_sql = """
            INSERT INTO document_chunks (source_id, chunk_index, content, embedding)
            VALUES %s
            ON CONFLICT (source_id, chunk_index)
            DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding
        """
        template = "(%s, %s, %s, %s::vector)"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                insert_sql,
                records,
                template=template,
                page_size=500,
            )
        conn.commit()
        logger.info(f"Successfully inserted/updated batch of {len(records)} chunks.")
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error(f"Batch insertion failed: {e}")
        raise
    finally:
        release_connection(conn)


def delete_chunks_by_source_id(source_id: str) -> int:
    """Deletes all chunks belonging to source_id.

    Args:
        source_id: Unique identifier for the source document.

    Returns:
        int: Number of rows deleted.
    """
    if not source_id:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM document_chunks WHERE source_id = %s;",
                (source_id,),
            )
            rc = cur.rowcount
            deleted_count = rc if rc is not None and rc > 0 else 0
        conn.commit()
        logger.info(f"Deleted {deleted_count} chunks for source_id '{source_id}'.")
        return deleted_count
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete chunks for source_id '{source_id}': {e}")
        raise
    finally:
        release_connection(conn)


def cleanup_test_data(source_prefix: str, batch_size: int = 5000) -> int:
    """Safely deletes all chunks where source_id LIKE f'{source_prefix}%' in batches.

    Executes batched deletion using a subquery with LIMIT and commits each batch
    independently to minimize lock contention and WAL growth. Continues until no
    matching rows remain.

    Args:
        source_prefix: Prefix of source_id identifying records to delete.
        batch_size: Maximum number of rows to delete per batch (default 5000).

    Returns:
        int: Total number of deleted rows.
    """
    if not source_prefix:
        return 0
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")

    like_pattern = f"{source_prefix}%"
    total_deleted = 0
    conn = get_connection()
    try:
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE id IN (
                        SELECT id FROM document_chunks
                        WHERE source_id LIKE %s
                        LIMIT %s
                    );
                    """,
                    (like_pattern, batch_size),
                )
                rc = cur.rowcount
                batch_deleted = rc if rc is not None and rc > 0 else 0
            conn.commit()
            total_deleted += batch_deleted
            if batch_deleted < batch_size:
                break
        logger.info(f"Cleaned up total of {total_deleted} chunks with prefix '{source_prefix}'.")
        return total_deleted
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to cleanup test data for prefix '{source_prefix}': {e}")
        raise
    finally:
        release_connection(conn)


def get_chunk_count(source_prefix: Optional[str] = None) -> int:
    """Returns total count of document chunks, optionally filtered by source_id prefix.

    Args:
        source_prefix: Optional prefix filter for source_id (matching source_id LIKE '{source_prefix}%').
                       If None, counts all document_chunks in the table.

    Returns:
        int: Total matching row count.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if source_prefix is None:
                cur.execute("SELECT COUNT(*) FROM document_chunks;")
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE source_id LIKE %s;",
                    (f"{source_prefix}%",),
                )
            row = cur.fetchone()
            count = int(row[0]) if row and row[0] is not None else 0
        conn.commit()
        return count
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to get chunk count (prefix={source_prefix}): {e}")
        raise
    finally:
        release_connection(conn)


def upsert_document_record(
    doc_id: str,
    filename: str,
    source_type: str,
    file_size_bytes: int = 0,
    chunk_count: int = 0,
    status: str = "queued",
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Upserts document metadata into documents table using ThreadedConnectionPool.

    Args:
        doc_id: Unique document identifier.
        filename: Original file name.
        source_type: Source format ('pdf', 'docx', 'txt', 'md', 'csv', 'url', etc.).
        file_size_bytes: Size of the raw file in bytes.
        chunk_count: Number of chunks generated.
        status: Ingestion status ('queued', 'processing', 'indexed', 'failed').
        error_message: Optional failure explanation.

    Returns:
        Dict[str, Any]: The inserted or updated document record dictionary.
    """
    if not doc_id:
        raise ValueError("doc_id cannot be empty")
    if not filename:
        raise ValueError("filename cannot be empty")
    if not source_type:
        raise ValueError("source_type cannot be empty")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    doc_id, filename, source_type, file_size_bytes, chunk_count, status, error_message, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (doc_id)
                DO UPDATE SET
                    filename = EXCLUDED.filename,
                    source_type = EXCLUDED.source_type,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    chunk_count = EXCLUDED.chunk_count,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
                RETURNING doc_id, filename, source_type, file_size_bytes, chunk_count, status, error_message, created_at;
                """,
                (doc_id, filename, source_type, file_size_bytes, chunk_count, status, error_message),
            )
            row = cur.fetchone()
        conn.commit()

        if not row:
            raise RuntimeError(f"Failed to upsert document record for doc_id '{doc_id}'")

        return {
            "doc_id": row[0],
            "filename": row[1],
            "source_type": row[2],
            "file_size_bytes": int(row[3] or 0),
            "chunk_count": int(row[4] or 0),
            "status": row[5],
            "error_message": row[6],
            "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else (str(row[7]) if row[7] is not None else None),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upsert document record (doc_id={doc_id}): {e}")
        raise
    finally:
        release_connection(conn)


def update_document_status(
    doc_id: str,
    status: str,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
) -> bool:
    """Updates status ('queued', 'processing', 'indexed', 'failed'), error message,
    and optionally chunk_count for a document in the documents table.

    Args:
        doc_id: Unique document identifier.
        status: Ingestion status string.
        error_message: Optional error message.
        chunk_count: Optional chunk count integer.

    Returns:
        bool: True if a record was updated, False otherwise.
    """
    if not doc_id:
        return False

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if chunk_count is not None:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s,
                        chunk_count = %s
                    WHERE doc_id = %s;
                    """,
                    (status, error_message, chunk_count, doc_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s
                    WHERE doc_id = %s;
                    """,
                    (status, error_message, doc_id),
                )
            rc = cur.rowcount
            updated = bool(rc is not None and rc > 0)
        conn.commit()
        return updated
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update document status for doc_id '{doc_id}': {e}")
        raise
    finally:
        release_connection(conn)


def list_documents() -> Dict[str, Any]:
    """Retrieves all documents and calculates overall corpus statistics.

    Returns:
        Dict[str, Any]: {
            "documents": List[Dict[str, Any]],
            "total_documents": int,
            "total_chunks": int,
            "total_size_bytes": int
        }
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_id, filename, source_type, file_size_bytes, chunk_count, status, error_message, created_at
                FROM documents
                ORDER BY created_at DESC;
                """
            )
            rows = cur.fetchall() or []

            cur.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(chunk_count), 0),
                    COALESCE(SUM(file_size_bytes), 0)
                FROM documents;
                """
            )
            stats = cur.fetchone()

        conn.commit()

        docs = []
        for r in rows:
            docs.append({
                "doc_id": r[0],
                "filename": r[1],
                "source_type": r[2],
                "file_size_bytes": int(r[3] or 0),
                "chunk_count": int(r[4] or 0),
                "status": r[5],
                "error_message": r[6],
                "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else (str(r[7]) if r[7] is not None else None),
            })

        total_docs = int(stats[0] or 0) if stats else len(docs)
        total_chunks = int(stats[1] or 0) if stats else sum(d["chunk_count"] for d in docs)
        total_size = int(stats[2] or 0) if stats else sum(d["file_size_bytes"] for d in docs)

        return {
            "documents": docs,
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size,
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to list documents: {e}")
        raise
    finally:
        release_connection(conn)


def delete_document(doc_id: str) -> bool:
    """Deletes document from documents table.

    Foreign key constraint ON DELETE CASCADE automatically purges all
    associated chunks and vectors from document_chunks.

    Args:
        doc_id: Unique document identifier.

    Returns:
        bool: True if the document was found and deleted, False otherwise.
    """
    if not doc_id:
        return False

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE doc_id = %s;",
                (doc_id,),
            )
            rc = cur.rowcount
            deleted = bool(rc is not None and rc > 0)
        conn.commit()
        logger.info(f"Deleted document '{doc_id}' (success={deleted}).")
        return deleted
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete document '{doc_id}': {e}")
        raise
    finally:
        release_connection(conn)


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a single document by doc_id.

    Args:
        doc_id: Unique document identifier.

    Returns:
        Optional[Dict[str, Any]]: Document metadata dict if found, None otherwise.
    """
    if not doc_id:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_id, filename, source_type, file_size_bytes, chunk_count, status, error_message, created_at
                FROM documents
                WHERE doc_id = %s;
                """,
                (doc_id,),
            )
            row = cur.fetchone()
        conn.commit()

        if not row:
            return None

        return {
            "doc_id": row[0],
            "filename": row[1],
            "source_type": row[2],
            "file_size_bytes": int(row[3] or 0),
            "chunk_count": int(row[4] or 0),
            "status": row[5],
            "error_message": row[6],
            "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else (str(row[7]) if row[7] is not None else None),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to get document '{doc_id}': {e}")
        raise
    finally:
        release_connection(conn)


__all__ = [
    "get_pool",
    "get_connection",
    "release_connection",
    "get_db_connection",
    "close_pool",
    "_format_embedding",
    "init_db",
    "insert_chunks_batch",
    "delete_chunks_by_source_id",
    "cleanup_test_data",
    "get_chunk_count",
    "upsert_document_record",
    "update_document_status",
    "list_documents",
    "delete_document",
    "get_document",
]
