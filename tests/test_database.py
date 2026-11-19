"""
Automated Pytest Suite for StrataSearch Database & Storage Hardening Layer (Milestone 1).

Coverage:
1. Embedding Formatter Robustness (_format_embedding):
   - None returns None
   - 1D list / tuple of floats & ints
   - 1D numpy ndarray (float32, float64)
   - Pre-formatted vector string validation
   - Strict rejection: booleans, dicts, sets, non-numeric strings, multi-dim arrays, empty sequences
2. Connection Pool Transaction Leak Prevention:
   - Connection release with IDLE transaction
   - Connection release with INTRANS (idle in transaction) -> automatic rollback
   - Connection release with INERROR (aborted transaction) -> automatic rollback
   - Connection release with closed or broken connection -> putconn(close=True)
   - get_db_connection context manager rollback on exception and guaranteed release
   - ThreadedConnectionPool lazy initialization and close_pool
3. Schema Initialization & Deduplication Constraints:
   - init_db creates pgvector extension, table, HNSW, GIN, B-tree indexes
   - UNIQUE constraint 'uq_document_chunks_source_chunk' on (source_id, chunk_index)
   - CREATE UNIQUE INDEX IF NOT EXISTS on (source_id, chunk_index)
4. Batch Insertion with Conflict Resolution (insert_chunks_batch):
   - High-speed execute_values insertion
   - Upsert ON CONFLICT (source_id, chunk_index) DO UPDATE
   - Batch size validation (mismatched chunks and embeddings)
   - Empty batch handling
   - Transaction rollback on SQL failure
5. Per-Source Deletion (delete_chunks_by_source_id):
   - Deletion of source chunks with exact row count returned
   - Empty source_id safety guard
   - Transaction rollback on error
6. Batched Test Data Cleanup (cleanup_test_data):
   - Prefix matching with subquery LIMIT
   - Multi-batch cascading deletion with explicit per-batch commits
   - Termination when zero records remain
   - Empty prefix safety guard and invalid batch_size rejection
7. Row Count Inspection (get_chunk_count):
   - Table-wide count (source_prefix=None)
   - Prefix-filtered count (source_id LIKE 'prefix%')
   - Transaction commit/closure after SELECT
"""

import sys
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, call, patch
import numpy as np
import pytest
import psycopg2
import psycopg2.extensions as ext

from app.database import (
    _format_embedding,
    cleanup_test_data,
    close_pool,
    delete_chunks_by_source_id,
    get_chunk_count,
    get_connection,
    get_db_connection,
    get_pool,
    init_db,
    insert_chunks_batch,
    release_connection,
)


# ===========================================================================
# 1. Embedding Formatter Robustness Tests
# ===========================================================================
class TestEmbeddingFormatter:
    def test_format_embedding_none(self):
        """None input must cleanly return None."""
        assert _format_embedding(None) is None

    def test_format_embedding_float_list(self):
        """List of standard floats must be formatted into '[x,y,z]'."""
        emb = [0.12345, -0.6789, 0.0]
        formatted = _format_embedding(emb)
        assert formatted == "[0.12345,-0.6789,0.0]"

    def test_format_embedding_int_list(self):
        """List of integers must be cast to floats in '[x,y,z]'."""
        emb = [1, 2, -3]
        formatted = _format_embedding(emb)
        assert formatted == "[1.0,2.0,-3.0]"

    def test_format_embedding_tuple(self):
        """Tuples of numeric types must be supported."""
        emb = (0.5, 1.5, -2.5)
        formatted = _format_embedding(emb)
        assert formatted == "[0.5,1.5,-2.5]"

    def test_format_embedding_numpy_1d_float32(self):
        """1D numpy float32 ndarray must format correctly."""
        arr = np.array([0.1, -0.2, 0.3], dtype=np.float32)
        formatted = _format_embedding(arr)
        assert formatted.startswith("[") and formatted.endswith("]")
        # Verify parseable as floats
        vals = [float(x) for x in formatted[1:-1].split(",")]
        assert len(vals) == 3
        assert pytest.approx(vals[0], rel=1e-5) == 0.1
        assert pytest.approx(vals[1], rel=1e-5) == -0.2
        assert pytest.approx(vals[2], rel=1e-5) == 0.3

    def test_format_embedding_numpy_1d_float64(self):
        """1D numpy float64 ndarray must format correctly."""
        arr = np.array([1.23456789, -9.87654321], dtype=np.float64)
        formatted = _format_embedding(arr)
        vals = [float(x) for x in formatted[1:-1].split(",")]
        assert pytest.approx(vals[0], rel=1e-7) == 1.23456789
        assert pytest.approx(vals[1], rel=1e-7) == -9.87654321

    def test_format_embedding_valid_pgvector_string(self):
        """Valid pre-formatted vector strings must be validated and returned."""
        raw = " [ 0.1, -0.25, 3.14 ] "
        formatted = _format_embedding(raw)
        assert formatted == "[ 0.1, -0.25, 3.14 ]"

    def test_format_embedding_reject_boolean(self):
        """Booleans must be explicitly rejected even though bool is a subclass of int."""
        with pytest.raises(TypeError, match="Invalid embedding type bool"):
            _format_embedding(True)
        with pytest.raises(TypeError, match="Non-numeric element.*bool"):
            _format_embedding([1.0, False, 2.0])

    def test_format_embedding_reject_dict_and_set(self):
        """Dictionaries, sets, and unsupported object types must raise TypeError."""
        with pytest.raises(TypeError):
            _format_embedding({"embedding": [0.1, 0.2]})
        with pytest.raises(TypeError):
            _format_embedding({0.1, 0.2, 0.3})
        with pytest.raises(TypeError):
            _format_embedding(object())

    def test_format_embedding_reject_non_numeric_elements(self):
        """Lists with strings or objects as elements must raise TypeError."""
        with pytest.raises(TypeError, match="Non-numeric element"):
            _format_embedding(["0.1", "0.2"])
        with pytest.raises(TypeError, match="Non-numeric element"):
            _format_embedding([0.1, None, 0.3])

    def test_format_embedding_reject_multidimensional_numpy(self):
        """2D or multi-dimensional numpy arrays must raise ValueError."""
        arr_2d = np.zeros((2, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="Embedding array must be 1-dimensional"):
            _format_embedding(arr_2d)

    def test_format_embedding_reject_malformed_string(self):
        """Strings not starting with '[' or containing non-numerics must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid pgvector string representation"):
            _format_embedding("not_a_vector")
        with pytest.raises(ValueError, match="Invalid pgvector string representation"):
            _format_embedding("0.1, 0.2, 0.3")
        with pytest.raises(ValueError, match="Non-numeric component"):
            _format_embedding("[0.1, invalid_token, 0.3]")
        with pytest.raises(ValueError, match="Empty vector string"):
            _format_embedding("[]")
        with pytest.raises(ValueError, match="Malformed vector string"):
            _format_embedding("[0.1,,0.2]")

    def test_format_embedding_reject_empty_sequence(self):
        """Empty lists or tuples must raise ValueError."""
        with pytest.raises(ValueError, match="Embedding sequence cannot be empty"):
            _format_embedding([])
        with pytest.raises(ValueError, match="Embedding sequence cannot be empty"):
            _format_embedding(())

    def test_format_embedding_reject_nan_and_inf(self):
        """NaN and Inf float values must be rejected with ValueError to protect vector index integrity."""
        with pytest.raises(ValueError, match="(?i)nan|inf|invalid"):
            _format_embedding([float("nan"), 0.1, 0.2])
        with pytest.raises(ValueError, match="(?i)nan|inf|invalid"):
            _format_embedding([0.1, float("inf"), 0.2])
        with pytest.raises(ValueError, match="(?i)nan|inf|invalid"):
            _format_embedding(np.array([float("nan"), 0.5], dtype=np.float32))
        with pytest.raises(ValueError, match="(?i)nan|inf|invalid"):
            _format_embedding(np.array([float("inf"), 0.5], dtype=np.float32))


# ===========================================================================
# 2. Connection Pool & Transaction Leak Prevention Tests
# ===========================================================================
class TestConnectionPoolAndLeaks:
    def test_release_connection_none_safe(self):
        """Passing None to release_connection must be a safe no-op."""
        release_connection(None)

    def test_release_connection_idle_transaction(self):
        """Connection in IDLE state is returned to pool without calling rollback."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_pool", return_value=mock_pool):
            release_connection(mock_conn)

        mock_conn.rollback.assert_not_called()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_intrans_triggers_rollback(self):
        """Connection left in TRANSACTION_STATUS_INTRANS must trigger rollback before putconn."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INTRANS
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_pool", return_value=mock_pool):
            release_connection(mock_conn)

        # Verified: rollback was executed to eliminate idle-in-transaction leak
        mock_conn.rollback.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_inerror_triggers_rollback(self):
        """Connection left in TRANSACTION_STATUS_INERROR must trigger rollback before putconn."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INERROR
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_pool", return_value=mock_pool):
            release_connection(mock_conn)

        mock_conn.rollback.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_rollback_failure_closes_and_discards(self):
        """If rollback fails (e.g. broken socket), connection must be closed and discarded with close=True."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INTRANS
        mock_conn.rollback.side_effect = psycopg2.DatabaseError("Connection reset by peer")
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_pool", return_value=mock_pool):
            release_connection(mock_conn)

        mock_conn.close.assert_called_once()

    def test_release_connection_already_closed(self):
        """If connection is already marked closed, putconn must be called with close=True."""
        mock_conn = MagicMock()
        mock_conn.closed = 1
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_pool", return_value=mock_pool):
            release_connection(mock_conn)

        mock_pool.putconn.assert_called_once_with(mock_conn, close=True)

    def test_get_db_connection_normal_flow(self):
        """Context manager yields connection and releases it on exit."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            with get_db_connection() as conn:
                assert conn is mock_conn
                # Connection is active inside block

        # On block exit, release_connection must have put conn back
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_get_db_connection_exception_triggers_rollback_and_release(self):
        """Context manager catches exception, invokes rollback, re-raises, and releases conn."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INTRANS
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            with pytest.raises(RuntimeError, match="Simulated crash"):
                with get_db_connection():
                    raise RuntimeError("Simulated crash")

        # Rollback was called on exception
        assert mock_conn.rollback.call_count >= 1
        # Connection was safely released
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_close_pool(self):
        """close_pool() calls closeall on the pool and resets global reference."""
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database._pool", mock_pool):
            close_pool()
            mock_pool.closeall.assert_called_once()


# ===========================================================================
# 3. Schema Initialization & Deduplication Constraints
# ===========================================================================
class TestDatabaseSchemaAndInit:
    def test_init_db_executes_ddl_and_unique_constraint(self):
        """init_db must create table with UNIQUE constraint and unique index."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.register_vector") as mock_reg, \
             patch("app.database.get_pool", return_value=mock_pool):
            init_db(max_retries=1)

        # Collect executed SQL strings
        executed_sqls = [call_args[0][0] for call_args in mock_cur.execute.call_args_list]
        combined_sql = "\n".join(executed_sqls)

        # 1. pgvector extension
        assert "CREATE EXTENSION IF NOT EXISTS vector" in combined_sql
        # 2. Table definition with UNIQUE constraint
        assert "CREATE TABLE IF NOT EXISTS document_chunks" in combined_sql
        assert "uq_document_chunks_source_chunk UNIQUE (source_id, chunk_index)" in combined_sql
        # 3. Unique index for pre-existing tables
        assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_source_chunk" in combined_sql
        # 4. HNSW vector index
        assert "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw" in combined_sql
        # 5. GIN full-text index
        assert "CREATE INDEX IF NOT EXISTS idx_document_chunks_tsv_gin" in combined_sql
        # 6. B-tree index on source_id
        assert "CREATE INDEX IF NOT EXISTS idx_document_chunks_source_id" in combined_sql

        # Verify transaction commit
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_init_db_retries_on_operational_error(self):
        """init_db must retry up to max_retries on OperationalError."""
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        # Fail twice with OperationalError, succeed on 3rd attempt
        mock_get_conn = MagicMock(side_effect=[
            psycopg2.OperationalError("DB starting up"),
            psycopg2.OperationalError("DB starting up"),
            mock_conn,
        ])

        with patch("app.database.get_connection", mock_get_conn), \
             patch("app.database.register_vector"), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("time.sleep"):  # Do not actually wait in tests
            init_db(max_retries=3, retry_delay=0.01)

        assert mock_get_conn.call_count == 3
        mock_conn.commit.assert_called_once()


# ===========================================================================
# 4. Batch Insertion with Conflict Resolution
# ===========================================================================
class TestInsertChunksBatch:
    def test_insert_chunks_batch_empty_input(self):
        """Empty chunks list returns 0 without acquiring a DB connection."""
        with patch("app.database.get_connection") as mock_get_conn:
            result = insert_chunks_batch("doc-001", [], [])
            assert result == 0
            mock_get_conn.assert_not_called()

    def test_insert_chunks_batch_size_mismatch_raises_error(self):
        """Mismatched chunks and embeddings counts must raise ValueError."""
        with pytest.raises(ValueError, match="Mismatched batch sizes"):
            insert_chunks_batch("doc-001", ["chunk1", "chunk2"], [[0.1, 0.2]])

    def test_insert_chunks_batch_empty_chunks_with_embeddings_raises_error(self):
        """Empty chunks with non-empty embeddings is a batch mismatch and must raise ValueError."""
        with pytest.raises(ValueError, match="Mismatched batch sizes"):
            insert_chunks_batch("doc-mismatch-empty", [], [[0.1] * 384])

    def test_insert_chunks_batch_non_empty_chunks_with_empty_embeddings_raises_error(self):
        """Non-empty chunks with empty embeddings is a batch mismatch and must raise ValueError."""
        with pytest.raises(ValueError, match="Mismatched batch sizes"):
            insert_chunks_batch("doc-mismatch-empty2", ["Some chunk content"], [])

    def test_insert_chunks_batch_includes_on_conflict_clause(self):
        """Batch insert SQL must include ON CONFLICT DO UPDATE on (source_id, chunk_index)."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        chunks = ["Chunk text one", "Chunk text two"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("psycopg2.extras.execute_values") as mock_exec_values:
            count = insert_chunks_batch("test-source-id", chunks, embeddings)

        assert count == 2
        mock_exec_values.assert_called_once()
        sql_arg = mock_exec_values.call_args[0][1]
        records_arg = mock_exec_values.call_args[0][2]

        # Verify ON CONFLICT DO UPDATE clause is present
        assert "ON CONFLICT (source_id, chunk_index)" in sql_arg
        assert "DO UPDATE SET" in sql_arg
        assert "content = EXCLUDED.content" in sql_arg
        assert "embedding = EXCLUDED.embedding" in sql_arg

        # Verify records content
        assert len(records_arg) == 2
        assert records_arg[0] == ("test-source-id", 0, "Chunk text one", "[0.1,0.2,0.3]")
        assert records_arg[1] == ("test-source-id", 1, "Chunk text two", "[0.4,0.5,0.6]")

        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_insert_chunks_batch_with_numpy_embeddings(self):
        """insert_chunks_batch must seamlessly handle 2D numpy arrays or list of 1D arrays."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        chunks = ["First chunk", "Second chunk", "Third chunk"]
        embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ], dtype=np.float32)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("psycopg2.extras.execute_values") as mock_exec_values:
            count = insert_chunks_batch("numpy-source", chunks, embeddings)

        assert count == 3
        records = mock_exec_values.call_args[0][2]
        assert len(records) == 3
        assert records[0][0] == "numpy-source"
        assert records[0][1] == 0
        assert records[1][1] == 1
        assert records[2][1] == 2

    def test_insert_chunks_batch_with_start_chunk_index(self):
        """insert_chunks_batch with start_chunk_index offsets chunk indices correctly."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        chunks = ["Chunk 10 text", "Chunk 11 text", "Chunk 12 text"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("psycopg2.extras.execute_values") as mock_exec_values:
            count = insert_chunks_batch("src-offset", chunks, embeddings, start_chunk_index=10)

        assert count == 3
        records = mock_exec_values.call_args[0][2]
        assert len(records) == 3
        assert records[0] == ("src-offset", 10, "Chunk 10 text", "[0.1,0.2]")
        assert records[1] == ("src-offset", 11, "Chunk 11 text", "[0.3,0.4]")
        assert records[2] == ("src-offset", 12, "Chunk 12 text", "[0.5,0.6]")

    def test_insert_chunks_batch_rollback_on_failure(self):
        """Database errors during batch insert must trigger conn.rollback() and re-raise."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INERROR
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("psycopg2.extras.execute_values", side_effect=psycopg2.DatabaseError("Disk full")):
            with pytest.raises(psycopg2.DatabaseError, match="Disk full"):
                insert_chunks_batch("src-fail", ["text"], [[0.1, 0.2]])

        mock_conn.rollback.assert_called()
        mock_pool.putconn.assert_called_once()


# ===========================================================================
# 5. Per-Source Deletion Tests
# ===========================================================================
class TestDeleteChunksBySourceId:
    def test_delete_chunks_by_source_id_empty_string(self):
        """Empty or None source_id must return 0 without querying."""
        with patch("app.database.get_connection") as mock_get_conn:
            assert delete_chunks_by_source_id("") == 0
            assert delete_chunks_by_source_id(None) == 0
            mock_get_conn.assert_not_called()

    def test_delete_chunks_by_source_id_success(self):
        """delete_chunks_by_source_id executes DELETE with source_id and returns rowcount."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 42
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            deleted = delete_chunks_by_source_id("doc-uuid-99")

        assert deleted == 42
        mock_cur.execute.assert_called_once_with(
            "DELETE FROM document_chunks WHERE source_id = %s;",
            ("doc-uuid-99",),
        )
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_delete_chunks_by_source_id_rollback_on_error(self):
        """SQL error during delete must invoke conn.rollback()."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = psycopg2.DatabaseError("Deadlock detected")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INERROR
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            with pytest.raises(psycopg2.DatabaseError, match="Deadlock detected"):
                delete_chunks_by_source_id("doc-deadlock")

        mock_conn.rollback.assert_called()


# ===========================================================================
# 6. Batched Cleanup Utility Tests
# ===========================================================================
class TestCleanupTestData:
    def test_cleanup_test_data_empty_prefix_safe(self):
        """Empty prefix returns 0 without executing DELETE."""
        with patch("app.database.get_connection") as mock_get_conn:
            assert cleanup_test_data("") == 0
            assert cleanup_test_data(None) == 0
            mock_get_conn.assert_not_called()

    def test_cleanup_test_data_invalid_batch_size(self):
        """batch_size <= 0 must raise ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            cleanup_test_data("test_prefix", batch_size=0)
        with pytest.raises(ValueError, match="batch_size must be positive"):
            cleanup_test_data("test_prefix", batch_size=-100)

    def test_cleanup_test_data_single_batch(self):
        """When matching rows are less than batch_size, deletes in one batch and terminates."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 350
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            total_deleted = cleanup_test_data("stress_test_run1", batch_size=5000)

        assert total_deleted == 350
        assert mock_cur.execute.call_count == 1
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_cleanup_test_data_multiple_batches(self):
        """Deletes multiple batches, committing each, until last batch has < batch_size rows."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        # 3 batches: 5000, 5000, 1200 rows -> total 11200
        mock_cur_rowcounts = [5000, 5000, 1200]
        type(mock_cur).rowcount = property(lambda self: mock_cur_rowcounts.pop(0))
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            total = cleanup_test_data("stress_test_multi", batch_size=5000)

        assert total == 11200
        assert mock_conn.commit.call_count == 3
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_cleanup_test_data_rollback_on_failure(self):
        """Failure during batched deletion triggers rollback."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = psycopg2.OperationalError("Connection lost")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INERROR
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            with pytest.raises(psycopg2.OperationalError, match="Connection lost"):
                cleanup_test_data("stress_test_prefix")

        mock_conn.rollback.assert_called()


# ===========================================================================
# 7. Database Row Count Inspection Tests
# ===========================================================================
class TestGetChunkCount:
    def test_get_chunk_count_without_prefix(self):
        """get_chunk_count(None) queries full table count and returns int."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1048576,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            count = get_chunk_count()

        assert count == 1048576
        mock_cur.execute.assert_called_once_with("SELECT COUNT(*) FROM document_chunks;")
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_get_chunk_count_with_prefix(self):
        """get_chunk_count('test_prefix') queries filtered count using LIKE 'test_prefix%'."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (543,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            count = get_chunk_count("test_stress_100k")

        assert count == 543
        mock_cur.execute.assert_called_once_with(
            "SELECT COUNT(*) FROM document_chunks WHERE source_id LIKE %s;",
            ("test_stress_100k%",),
        )
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_get_chunk_count_empty_table_returns_zero(self):
        """When query returns None or empty row, returns 0."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            count = get_chunk_count()

        assert count == 0

    def test_get_chunk_count_rollback_on_error(self):
        """SQL error during count triggers rollback."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = psycopg2.DatabaseError("Relation does not exist")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = 0
        mock_conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_INERROR
        mock_pool = MagicMock(closed=False)

        with patch("app.database.get_connection", return_value=mock_conn), \
             patch("app.database.get_pool", return_value=mock_pool):
            with pytest.raises(psycopg2.DatabaseError, match="Relation does not exist"):
                get_chunk_count()

        mock_conn.rollback.assert_called()


# ===========================================================================
# 8. Stateful Integration Simulation Tests
# ===========================================================================
class StatefulMockDatabase:
    """Simulates a stateful PostgreSQL database with transaction tracking and table storage.

    Verifies genuine behavior:
    - Tables and indexes creation
    - Unique constraint enforcement and ON CONFLICT upserting
    - Deletion and cascading batched cleanup
    - Row count inspection
    - Transaction state transitions (IDLE -> INTRANS -> IDLE on commit/rollback)
    """

    def __init__(self):
        self.chunks_table: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self.next_id = 1
        self.transaction_status = ext.TRANSACTION_STATUS_IDLE
        self.closed = 0

    def get_transaction_status(self):
        return self.transaction_status

    def commit(self):
        self.transaction_status = ext.TRANSACTION_STATUS_IDLE

    def rollback(self):
        self.transaction_status = ext.TRANSACTION_STATUS_IDLE

    def close(self):
        self.closed = 1

    def cursor(self):
        return StatefulMockCursor(self)


class StatefulMockCursor:
    def __init__(self, db: StatefulMockDatabase):
        self.db = db
        self.rowcount = 0
        self._last_fetch = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query: str, params: Any = None):
        self.db.transaction_status = ext.TRANSACTION_STATUS_INTRANS
        normalized = " ".join(query.strip().split())

        if "CREATE TABLE" in normalized or "CREATE EXTENSION" in normalized or "INDEX" in normalized:
            self.rowcount = -1
            return

        if normalized.startswith("DELETE FROM document_chunks WHERE source_id = %s"):
            src_id = params[0]
            to_delete = [k for k in self.db.chunks_table.keys() if k[0] == src_id]
            for k in to_delete:
                del self.db.chunks_table[k]
            self.rowcount = len(to_delete)
            return

        if "DELETE FROM document_chunks WHERE id IN" in normalized:
            prefix_pattern = params[0]  # e.g. "prefix%"
            prefix = prefix_pattern.rstrip("%")
            limit = params[1]
            matching_keys = [k for k in self.db.chunks_table.keys() if k[0].startswith(prefix)]
            keys_to_delete = matching_keys[:limit]
            for k in keys_to_delete:
                del self.db.chunks_table[k]
            self.rowcount = len(keys_to_delete)
            return

        if normalized.startswith("SELECT COUNT(*) FROM document_chunks"):
            if "WHERE source_id LIKE %s" in normalized:
                prefix = params[0].rstrip("%")
                count = sum(1 for k in self.db.chunks_table.keys() if k[0].startswith(prefix))
            else:
                count = len(self.db.chunks_table)
            self._last_fetch = (count,)
            return

        raise NotImplementedError(f"Query not handled by mock: {query}")

    def fetchone(self):
        return self._last_fetch


class TestStatefulDatabaseSimulation:
    def test_full_stateful_lifecycle(self):
        """End-to-end stateful test simulating schema init, insert, upsert, count, delete, batched cleanup."""
        db = StatefulMockDatabase()
        mock_pool = MagicMock(closed=False)
        mock_pool.closed = False

        # Intercept execute_values to write to db.chunks_table
        def mock_execute_values(cur, sql, records, **kwargs):
            db.transaction_status = ext.TRANSACTION_STATUS_INTRANS
            for rec in records:
                source_id, chunk_index, content, embedding = rec
                key = (source_id, chunk_index)
                if key in db.chunks_table:
                    # Upsert behavior
                    db.chunks_table[key]["content"] = content
                    db.chunks_table[key]["embedding"] = embedding
                else:
                    db.chunks_table[key] = {
                        "id": db.next_id,
                        "source_id": source_id,
                        "chunk_index": chunk_index,
                        "content": content,
                        "embedding": embedding,
                    }
                    db.next_id += 1

        with patch("app.database.get_connection", return_value=db), \
             patch("app.database.get_pool", return_value=mock_pool), \
             patch("psycopg2.extras.execute_values", side_effect=mock_execute_values), \
             patch("app.database.register_vector"):

            # Step 1: Initialize DB schema
            init_db()
            assert db.transaction_status == ext.TRANSACTION_STATUS_IDLE

            # Step 2: Insert initial batch of 3 chunks
            chunks_doc1 = ["chunk 0", "chunk 1", "chunk 2"]
            embs_doc1 = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
            inserted = insert_chunks_batch("doc_001", chunks_doc1, embs_doc1)
            assert inserted == 3
            assert get_chunk_count() == 3
            assert get_chunk_count("doc_001") == 3
            assert get_chunk_count("doc_002") == 0

            # Step 3: Re-ingest with updated content on same (source_id, chunk_index) -> verify UPSERT
            updated_chunks_doc1 = ["updated chunk 0", "chunk 1", "chunk 2"]
            insert_chunks_batch("doc_001", updated_chunks_doc1, embs_doc1)
            # Count must still be 3 (no duplicate rows created!)
            assert get_chunk_count() == 3
            assert db.chunks_table[("doc_001", 0)]["content"] == "updated chunk 0"

            # Step 4: Insert another document with 5 chunks
            chunks_doc2 = [f"doc2 chunk {i}" for i in range(5)]
            embs_doc2 = [[0.1 * i, 0.2 * i] for i in range(5)]
            insert_chunks_batch("doc_002", chunks_doc2, embs_doc2)
            assert get_chunk_count() == 8
            assert get_chunk_count("doc_001") == 3
            assert get_chunk_count("doc_002") == 5

            # Step 5: Insert test stress data with prefix 'test_stress_100k:'
            for batch_num in range(12):
                src = f"test_stress_100k:run_{batch_num}"
                insert_chunks_batch(src, [f"stress chunk {j}" for j in range(10)], [[0.1, 0.2]] * 10)

            # Total is now 8 + 120 = 128
            assert get_chunk_count() == 128
            assert get_chunk_count("test_stress_100k:") == 120

            # Step 6: Test single-source deletion
            deleted = delete_chunks_by_source_id("doc_001")
            assert deleted == 3
            assert get_chunk_count("doc_001") == 0
            assert get_chunk_count() == 125

            # Step 7: Test batched cleanup with small batch size
            cleaned = cleanup_test_data("test_stress_100k:", batch_size=25)
            assert cleaned == 120
            # Verify 0-residual records for test_stress_100k
            assert get_chunk_count("test_stress_100k:") == 0
            # Only doc_002 (5 chunks) remains in database
            assert get_chunk_count() == 5
            assert get_chunk_count("doc_002") == 5
