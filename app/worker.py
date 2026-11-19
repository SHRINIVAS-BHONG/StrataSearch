"""
Celery Worker module for asynchronous document ingestion and embedding in StrataSearch.

Features:
- Configures Celery application pointing to Redis broker & backend.
- Asynchronous task ingest_document_task with automatic exponential backoff retry and status tracking.
- Synchronous fallback execution (process_document_sync and dispatch_ingest_task) for SINGLE_NODE_MODE or broker-offline environments.
- Integrates semantic chunking, normalized dense embedding generation, and high-speed batch DB insertion.
- Document status transitions via update_document_status ('processing' -> 'indexed' / 'failed').
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
from celery import Celery

try:
    from app.config import REDIS_URL
except ImportError:
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    from app.config import SINGLE_NODE_MODE
except (ImportError, AttributeError):
    SINGLE_NODE_MODE = os.getenv("SINGLE_NODE_MODE", "false").lower() in ("true", "1", "yes")

from app.database import delete_chunks_by_source_id, insert_chunks_batch
from app.ingest import embedder, sanitize_text, semantic_chunk_text

try:
    from app.database import update_document_status
except (ImportError, AttributeError):
    def update_document_status(
        doc_id: str,
        status: str,
        error_message: Optional[str] = None,
        chunk_count: Optional[int] = None,
    ) -> bool:
        """Fallback dynamic resolver for update_document_status."""
        try:
            from app import database
            fn = getattr(database, "update_document_status", None)
            if fn and callable(fn):
                return fn(doc_id, status, error_message=error_message, chunk_count=chunk_count)
        except Exception:
            pass
        return False

logger = logging.getLogger(__name__)

SUB_BATCH_SIZE: int = 64


def partition_chunks(chunks: List[str], batch_size: int = SUB_BATCH_SIZE) -> List[List[str]]:
    """Partitions a list of chunks into sub-batches of maximum size batch_size.

    Args:
        chunks: List of text chunk strings.
        batch_size: Maximum number of chunks per sub-batch (default SUB_BATCH_SIZE=64).

    Returns:
        List of sub-batch lists.
    """
    if not chunks:
        return []
    if batch_size <= 0:
        batch_size = SUB_BATCH_SIZE
    return [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]


def _report_progress(task: Any, current: int, total: int, source_id: str) -> None:
    """Updates Celery task state to PROGRESS with metadata, safely handling unbacked offline execution.

    Args:
        task: Bound Celery task instance.
        current: Number of chunks processed so far.
        total: Total number of chunks in document.
        source_id: Source document identifier.
    """
    if task is not None and hasattr(task, "update_state"):
        try:
            task.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total,
                    "source_id": source_id,
                },
            )
        except Exception as err:
            logger.debug("Task update_state skipped (broker unavailable or offline): %s", err)


class SyncTaskResult(dict):
    """Result wrapper simulating Celery AsyncResult for synchronous task execution."""

    def __init__(
        self,
        task_id: str,
        status: str = "SUCCESS",
        result: Optional[Dict[str, Any]] = None,
    ):
        res = dict(result or {})
        super().__init__(res)
        self["task_id"] = task_id
        self["id"] = task_id
        self.id = task_id
        self.status = status
        self.result = res

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self.result

    def ready(self) -> bool:
        return True

    def successful(self) -> bool:
        return self.status == "SUCCESS"

    def __str__(self) -> str:
        return self.id


# ---------------------------------------------------------------------------
# Celery Application Configuration
# ---------------------------------------------------------------------------
celery_app = Celery(
    "rag_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per document
    broker_connection_retry_on_startup=True,
)


# ---------------------------------------------------------------------------
# Synchronous Document Ingestion Routine
# ---------------------------------------------------------------------------
def process_document_sync(
    doc_id: str,
    raw_text: str,
    filename: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronously processes, chunks, embeds, and stores a document in PostgreSQL.

    Used when SINGLE_NODE_MODE=True or Celery broker is unavailable.
    Transitions document status:
    - 'processing' at task start
    - 'indexed' with chunk_count on success
    - 'failed' with error_message on error

    Args:
        doc_id: Unique document identifier.
        raw_text: Raw or extracted text of the document.
        filename: Optional original document filename.
        source_type: Optional source format type.

    Returns:
        Dict summarizing doc_id, source_id, chunks_count, and execution status.
    """
    effective_id = doc_id
    logger.info(
        "Starting synchronous ingestion for doc_id: %s (filename=%s, type=%s, length=%d)",
        effective_id,
        filename,
        source_type,
        len(raw_text or ""),
    )

    # Transition status to 'processing'
    try:
        update_document_status(effective_id, "processing")
    except Exception as status_err:
        logger.warning("Could not transition status to 'processing' for '%s': %s", effective_id, status_err)

    clean_text = sanitize_text(raw_text)
    if not clean_text or not clean_text.strip():
        logger.warning("Empty raw_text provided for doc: %s. Skipping ingestion.", effective_id)
        try:
            update_document_status(effective_id, "failed", error_message="Empty raw text provided", chunk_count=0)
        except Exception:
            pass
        return {
            "doc_id": effective_id,
            "source_id": effective_id,
            "filename": filename,
            "source_type": source_type,
            "chunks_count": 0,
            "status": "empty_document",
        }

    try:
        # Step 1: Semantic chunking on sentence boundaries
        chunks = semantic_chunk_text(clean_text, max_words=180, overlap_words=30)
        if not chunks:
            logger.warning("No chunks generated for doc: %s", effective_id)
            try:
                update_document_status(effective_id, "failed", error_message="No semantic chunks generated", chunk_count=0)
            except Exception:
                pass
            return {
                "doc_id": effective_id,
                "source_id": effective_id,
                "filename": filename,
                "source_type": source_type,
                "chunks_count": 0,
                "status": "no_chunks_generated",
            }

        total_chunks = len(chunks)
        logger.info("Generated %d semantic chunks for doc '%s'. Computing embeddings...", total_chunks, effective_id)

        # Step 2: Dense embedding generation with sub-batching (SUB_BATCH_SIZE=64)
        sub_batches = partition_chunks(chunks, batch_size=SUB_BATCH_SIZE)
        embeddings_batches: List[Any] = []
        for batch in sub_batches:
            batch_emb = embedder.encode(batch, normalize_embeddings=True)
            embeddings_batches.append(batch_emb)

        if embeddings_batches:
            if isinstance(embeddings_batches[0], np.ndarray):
                embeddings = np.vstack(embeddings_batches)
            else:
                embeddings = [emb for b in embeddings_batches for emb in b]
        else:
            embeddings = []

        # Step 3: Ingestion idempotency - eliminate existing chunks for this doc_id
        deleted_count = delete_chunks_by_source_id(effective_id)
        if deleted_count > 0:
            logger.info("Deleted %d existing chunks for doc '%s' before re-inserting.", deleted_count, effective_id)

        # Step 4: High-speed single-transaction batch insert into PostgreSQL
        try:
            inserted_count = insert_chunks_batch(effective_id, chunks, embeddings)
        except TypeError:
            tuples = [(effective_id, idx, c, emb) for idx, (c, emb) in enumerate(zip(chunks, embeddings))]
            inserted_count = insert_chunks_batch(tuples, doc_id=effective_id)

        logger.info("Successfully ingested %d chunks for doc '%s' (sync).", inserted_count, effective_id)

        # Step 5: Transition status to 'indexed' with chunk_count
        try:
            update_document_status(effective_id, "indexed", chunk_count=inserted_count)
        except Exception as status_err:
            logger.warning("Could not transition status to 'indexed' for '%s': %s", effective_id, status_err)

        return {
            "doc_id": effective_id,
            "source_id": effective_id,
            "filename": filename,
            "source_type": source_type,
            "chunks_count": inserted_count,
            "status": "success",
        }

    except Exception as exc:
        logger.error("Synchronous ingestion failed for doc '%s': %s", effective_id, exc)
        try:
            update_document_status(effective_id, "failed", error_message=str(exc))
        except Exception as status_err:
            logger.warning("Could not transition status to 'failed' for '%s': %s", effective_id, status_err)
        return {
            "doc_id": effective_id,
            "source_id": effective_id,
            "filename": filename,
            "source_type": source_type,
            "chunks_count": 0,
            "status": "failed",
            "error_message": str(exc),
        }


# ---------------------------------------------------------------------------
# Celery Task: Asynchronous Document Ingestion
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, max_retries=3)
def ingest_document_task(
    self,
    doc_id: Optional[str] = None,
    raw_text: str = "",
    filename: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Asynchronously processes a document:

    1. Transitions document status to 'processing' via update_document_status.
    2. Sanitizes and splits raw text into semantic chunks with sliding-window sentence overlap.
    3. Updates Celery task progress state to PROGRESS.
    4. Computes normalized dense vector embeddings in sub-batches of 64 to prevent worker OOM.
    5. Guarantees idempotency by deleting existing chunks for source_id before insertion.
    6. Batches insertions into PostgreSQL with pgvector using execute_values.
    7. Transitions document status to 'indexed' with chunk_count on success, or 'failed' on error.

    Args:
        self: Bound Celery task instance for retry handling and progress tracking.
        doc_id: Unique document identifier.
        raw_text: Raw or extracted text of the document.
        filename: Optional original document filename.
        source_type: Optional source format type ('pdf', 'docx', 'txt', 'url', etc.).
        source_id: Legacy document identifier for backward compatibility.

    Returns:
        Dict summarizing doc_id, source_id, chunks_count, and execution status.
    """
    effective_id = doc_id or source_id or ""
    logger.info(
        "Starting ingest_document_task for doc: %s (filename=%s, length=%d chars)",
        effective_id,
        filename,
        len(raw_text or ""),
    )

    # Transition status to 'processing' upon task start
    try:
        update_document_status(effective_id, "processing")
    except Exception as status_err:
        logger.warning("Could not transition status to 'processing' for '%s': %s", effective_id, status_err)

    clean_text = sanitize_text(raw_text)
    if not clean_text or not clean_text.strip():
        logger.warning("Empty raw_text provided for source: %s. Skipping ingestion.", effective_id)
        try:
            update_document_status(effective_id, "failed", error_message="Empty raw text provided", chunk_count=0)
        except Exception:
            pass
        return {
            "doc_id": effective_id,
            "source_id": effective_id,
            "filename": filename,
            "source_type": source_type,
            "chunks_count": 0,
            "status": "empty_document",
        }

    try:
        # Step 1: Semantic chunking on sentence boundaries
        chunks = semantic_chunk_text(clean_text, max_words=180, overlap_words=30)
        if not chunks:
            logger.warning("No chunks generated for source: %s", effective_id)
            try:
                update_document_status(effective_id, "failed", error_message="No semantic chunks generated", chunk_count=0)
            except Exception:
                pass
            return {
                "doc_id": effective_id,
                "source_id": effective_id,
                "filename": filename,
                "source_type": source_type,
                "chunks_count": 0,
                "status": "no_chunks_generated",
            }

        total_chunks = len(chunks)
        logger.info("Generated %d semantic chunks for source '%s'. Computing embeddings...", total_chunks, effective_id)

        # Initial progress state update
        _report_progress(self, current=0, total=total_chunks, source_id=effective_id)

        # Step 2: Dense embedding generation with sub-batching (SUB_BATCH_SIZE=64)
        sub_batches = partition_chunks(chunks, batch_size=SUB_BATCH_SIZE)
        embeddings_batches: List[Any] = []
        processed_chunks = 0

        for batch in sub_batches:
            batch_emb = embedder.encode(batch, normalize_embeddings=True)
            embeddings_batches.append(batch_emb)
            processed_chunks += len(batch)
            _report_progress(self, current=processed_chunks, total=total_chunks, source_id=effective_id)

        if embeddings_batches:
            if isinstance(embeddings_batches[0], np.ndarray):
                embeddings = np.vstack(embeddings_batches)
            else:
                embeddings = [emb for b in embeddings_batches for emb in b]
        else:
            embeddings = []

        # Step 3: Ingestion idempotency - eliminate existing chunks for this source_id
        deleted_count = delete_chunks_by_source_id(effective_id)
        if deleted_count > 0:
            logger.info("Deleted %d existing chunks for source '%s' before re-inserting.", deleted_count, effective_id)

        # Step 4: High-speed single-transaction batch insert into PostgreSQL
        try:
            inserted_count = insert_chunks_batch(effective_id, chunks, embeddings)
        except TypeError:
            tuples = [(effective_id, idx, c, emb) for idx, (c, emb) in enumerate(zip(chunks, embeddings))]
            inserted_count = insert_chunks_batch(tuples, doc_id=effective_id)

        logger.info("Successfully ingested %d chunks for source '%s'.", inserted_count, effective_id)

        # Step 5: Transition status to 'indexed' with chunk_count
        try:
            update_document_status(effective_id, "indexed", chunk_count=inserted_count)
        except Exception as status_err:
            logger.warning("Could not transition status to 'indexed' for '%s': %s", effective_id, status_err)

        return {
            "doc_id": effective_id,
            "source_id": effective_id,
            "filename": filename,
            "source_type": source_type,
            "chunks_count": inserted_count,
            "status": "success",
        }

    except Exception as exc:
        try:
            update_document_status(effective_id, "failed", error_message=str(exc))
        except Exception as status_err:
            logger.warning("Could not transition status to 'failed' for '%s': %s", effective_id, status_err)

        current_retries = getattr(getattr(self, "request", None), "retries", 0)
        max_retries = getattr(self, "max_retries", 3)
        retries_remaining = max_retries - current_retries
        logger.error(
            "Task failed for source '%s' (retries left: %d): %s",
            effective_id,
            retries_remaining,
            exc,
        )
        countdown = 2 ** (current_retries + 1)
        raise self.retry(exc=exc, countdown=countdown)


# ---------------------------------------------------------------------------
# Dispatch Helper: Synchronous vs Asynchronous Execution
# ---------------------------------------------------------------------------
def dispatch_ingest_task(
    doc_id: Optional[str] = None,
    raw_text: str = "",
    filename: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Dispatches document ingestion either synchronously or asynchronously:

    - If SINGLE_NODE_MODE=True or Celery broker is unreachable, executes synchronously via process_document_sync.
    - Otherwise, enqueues asynchronously via ingest_document_task.delay.

    Args:
        doc_id: Unique document identifier.
        raw_text: Text content to chunk and embed.
        filename: Optional original document filename.
        source_type: Optional document format type.
        source_id: Optional backward-compatible document ID.
        **kwargs: Additional parameters forwarded to the task.

    Returns:
        Celery AsyncResult or SyncTaskResult.
    """
    effective_id = doc_id or source_id or ""

    is_single_node = False
    try:
        from app.config import SINGLE_NODE_MODE as snm
        is_single_node = bool(snm)
    except (ImportError, AttributeError):
        is_single_node = os.getenv("SINGLE_NODE_MODE", "false").lower() in ("true", "1", "yes")

    if is_single_node:
        logger.info("SINGLE_NODE_MODE active: executing synchronous ingestion for doc_id=%s", effective_id)
        sync_res = process_document_sync(
            doc_id=effective_id,
            raw_text=raw_text,
            filename=filename,
            source_type=source_type,
        )
        task_status = "SUCCESS" if sync_res.get("status") in ("success", "empty_document", "no_chunks_generated") else "FAILURE"
        return SyncTaskResult(task_id=f"sync-{effective_id}", status=task_status, result=sync_res)

    try:
        return ingest_document_task.delay(
            doc_id=effective_id,
            raw_text=raw_text,
            filename=filename,
            source_type=source_type,
            **kwargs,
        )
    except Exception as broker_err:
        logger.warning(
            "Celery broker unavailable or task enqueue failed (%s). Falling back to synchronous processing for doc_id=%s.",
            broker_err,
            effective_id,
        )
        sync_res = process_document_sync(
            doc_id=effective_id,
            raw_text=raw_text,
            filename=filename,
            source_type=source_type,
        )
        task_status = "SUCCESS" if sync_res.get("status") in ("success", "empty_document", "no_chunks_generated") else "FAILURE"
        return SyncTaskResult(task_id=f"sync-{effective_id}", status=task_status, result=sync_res)


__all__ = [
    "celery_app",
    "ingest_document_task",
    "process_document_sync",
    "dispatch_ingest_task",
    "partition_chunks",
    "SUB_BATCH_SIZE",
    "SyncTaskResult",
    "update_document_status",
]
