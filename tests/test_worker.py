"""
Automated Pytest Suite for StrataSearch Background Celery Worker Pipeline.

Coverage:
1. Embedder Sub-Batching (Feature 9):
   - Sub-batch partitioning for large chunk lists (slices <= 64 items)
   - Exact multiple batch boundary handling (e.g., 128 chunks)
   - Single-chunk boundary condition (1 chunk)
   - Order preservation across sub-batches
   - Ingest task embedding sub-batching for >64 chunks (avoiding OOM)
2. Celery Task Progress Tracking (Feature 10):
   - State updates to PROGRESS with current and total chunk counts during execution
   - Task final return dictionary contract (source_id, chunks_count, status="success")
   - Empty and whitespace text handling (status="empty_document")
   - Task fallback when no chunks are generated
3. Ingestion Idempotency & Retry Resilience (Feature 11):
   - Pre-deletion before batch insertion for source_id idempotency
   - Verified execution order (delete strictly before insert)
   - Exponential backoff retry on database error (countdown = 2 ** (retries + 1))
   - Max retries calculation and exception propagation
"""

from typing import Any, List
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from celery.exceptions import Retry

from app.worker import (
    SUB_BATCH_SIZE,
    ingest_document_task,
    partition_chunks,
)


# ===========================================================================
# 1. Embedder Sub-Batching Tests (Feature 9)
# ===========================================================================
class TestWorkerSubBatching:
    def test_partition_chunks_large_list(self):
        """A list of 200 chunks with batch_size=64 must yield 4 slices: 64, 64, 64, 8."""
        chunks = [f"Chunk number {i} content text." for i in range(200)]
        batches = partition_chunks(chunks, batch_size=64)
        assert len(batches) == 4
        assert len(batches[0]) == 64
        assert len(batches[1]) == 64
        assert len(batches[2]) == 64
        assert len(batches[3]) == 8
        # Ensure elements and order are preserved
        flattened = [item for batch in batches for item in batch]
        assert flattened == chunks

    def test_partition_chunks_exact_multiple(self):
        """A list of exactly 128 chunks with batch_size=64 yields exactly 2 batches of 64."""
        chunks = [f"Chunk {i}" for i in range(128)]
        batches = partition_chunks(chunks, batch_size=64)
        assert len(batches) == 2
        assert len(batches[0]) == 64
        assert len(batches[1]) == 64

    def test_partition_chunks_single_chunk(self):
        """A single chunk produces exactly 1 batch containing 1 item."""
        chunks = ["Solo chunk text."]
        batches = partition_chunks(chunks, batch_size=64)
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0] == chunks

    def test_partition_chunks_empty_list(self):
        """Empty list yields empty batch list."""
        assert partition_chunks([], batch_size=64) == []

    def test_partition_chunks_invalid_or_zero_batch_size(self):
        """Zero or negative batch size safely defaults to SUB_BATCH_SIZE."""
        chunks = [f"Chunk {i}" for i in range(10)]
        batches = partition_chunks(chunks, batch_size=0)
        assert len(batches) == 1
        assert len(batches[0]) == 10

    def test_embedder_sub_batching_execution(self, mock_embedder):
        """Simulates sub-batched embedding encoding and concatenates results in order."""
        chunks = [f"Chunk item {i}" for i in range(150)]
        batch_size = 64

        batches = partition_chunks(chunks, batch_size=batch_size)
        all_embeddings = []
        for batch in batches:
            emb_batch = mock_embedder.encode(batch, normalize_embeddings=True)
            all_embeddings.append(emb_batch)

        combined = np.vstack(all_embeddings)
        assert combined.shape == (150, 384)

    def test_embedder_sub_batching_in_ingest_task(self, mock_embedder):
        """Documents with >64 chunks encode in sub-batches of <= 64 items preventing OOM."""
        mock_delete = MagicMock(return_value=0)
        mock_insert = MagicMock(return_value=150)
        encoded_batch_sizes: List[int] = []

        def spy_encode(sentences, normalize_embeddings=True, **kwargs):
            encoded_batch_sizes.append(len(sentences))
            return mock_embedder.encode(sentences, normalize_embeddings=normalize_embeddings, **kwargs)

        fake_chunks = [f"Chunk {i} semantic content." for i in range(150)]

        with patch("app.worker.semantic_chunk_text", return_value=fake_chunks), \
             patch("app.worker.embedder.encode", side_effect=spy_encode), \
             patch("app.worker.delete_chunks_by_source_id", mock_delete), \
             patch("app.worker.insert_chunks_batch", mock_insert):

            res = ingest_document_task("oom-prevention-doc", "Raw text for 150 chunks.")
            assert res["status"] == "success"
            assert res["chunks_count"] == 150

            # 150 chunks partitioned with batch size 64 -> 64, 64, 22
            assert len(encoded_batch_sizes) == 3
            assert encoded_batch_sizes == [64, 64, 22]
            for size in encoded_batch_sizes:
                assert size <= SUB_BATCH_SIZE


# ===========================================================================
# 2. Celery Task Execution & Progress Tracking Tests (Feature 10)
# ===========================================================================
class TestWorkerTaskExecution:
    def test_task_empty_document_handling(self):
        """Empty raw_text must return empty_document status without calling chunker or embedder."""
        res_empty = ingest_document_task("doc-empty-1", "")
        assert res_empty["status"] == "empty_document"
        assert res_empty["chunks_count"] == 0
        assert res_empty["source_id"] == "doc-empty-1"

        res_ws = ingest_document_task("doc-empty-2", "   \n\t  ")
        assert res_ws["status"] == "empty_document"
        assert res_ws["chunks_count"] == 0

    def test_task_success_execution_flow(self, mock_embedder):
        """Standard document must chunk, embed, pre-delete, insert, and return success dictionary."""
        mock_delete = MagicMock(return_value=2)
        mock_insert = MagicMock(return_value=3)

        with patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", mock_delete), \
             patch("app.worker.insert_chunks_batch", mock_insert):
            raw_text = (
                "PostgreSQL pgvector is high-performance. "
                "Reciprocal Rank Fusion fuses search modalities. "
                "Celery workers execute background tasks."
            )
            result = ingest_document_task("contract-test-doc", raw_text)

        assert result["status"] == "success"
        assert result["source_id"] == "contract-test-doc"
        assert result["chunks_count"] >= 1
        mock_delete.assert_called_once_with("contract-test-doc")
        mock_insert.assert_called_once()

    def test_task_progress_state_updates(self, mock_embedder):
        """Verifies Celery task update_state is actively called during ingestion with PROGRESS state."""
        mock_update_state = MagicMock()
        mock_delete = MagicMock(return_value=0)
        mock_insert = MagicMock(return_value=3)

        fake_chunks = ["Chunk A", "Chunk B", "Chunk C"]

        with patch.object(ingest_document_task, "update_state", mock_update_state), \
             patch("app.worker.semantic_chunk_text", return_value=fake_chunks), \
             patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", mock_delete), \
             patch("app.worker.insert_chunks_batch", mock_insert):

            result = ingest_document_task("progress-test-source", "Some raw text")
            assert result["status"] == "success"

        # Verify update_state calls
        assert mock_update_state.called
        assert mock_update_state.call_count >= 2  # initial (current=0) + at least 1 sub-batch

        first_call = mock_update_state.call_args_list[0]
        assert first_call.kwargs.get("state") == "PROGRESS"
        assert first_call.kwargs.get("meta") == {
            "current": 0,
            "total": 3,
            "source_id": "progress-test-source",
        }

        final_call = mock_update_state.call_args_list[-1]
        assert final_call.kwargs.get("state") == "PROGRESS"
        assert final_call.kwargs.get("meta") == {
            "current": 3,
            "total": 3,
            "source_id": "progress-test-source",
        }

    def test_task_no_chunks_generated_fallback(self):
        """When chunker returns empty list, returns no_chunks_generated status."""
        with patch("app.worker.semantic_chunk_text", return_value=[]):
            result = ingest_document_task("doc-no-chunks", "Some text that produces no chunks.")
            assert result["status"] == "no_chunks_generated"
            assert result["chunks_count"] == 0


# ===========================================================================
# 3. Ingestion Idempotency & Retry Resilience Tests (Feature 11)
# ===========================================================================
class TestWorkerRetryAndIdempotency:
    def test_worker_retry_backoff_on_database_error(self, mock_embedder):
        """Database error triggers task.retry with exponential backoff countdown."""
        mock_retry = MagicMock(side_effect=Retry("Retry triggered"))

        with patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", return_value=0), \
             patch("app.worker.insert_chunks_batch", side_effect=Exception("Database connection timeout")), \
             patch.object(ingest_document_task, "retry", mock_retry):

            # Simulate task execution at retry attempt 0
            ingest_document_task.request.retries = 0
            with pytest.raises(Retry):
                ingest_document_task("retry-doc-001", "Text requiring embedding and indexing.")

            # Exponential backoff at retries=0: 2 ** (0 + 1) = 2s
            mock_retry.assert_called_once()
            _, kwargs = mock_retry.call_args
            assert kwargs.get("countdown") == 2

    def test_worker_retry_backoff_on_pre_delete_error(self, mock_embedder):
        """Error during delete_chunks_by_source_id also triggers retry with backoff."""
        mock_retry = MagicMock(side_effect=Retry("Retry triggered"))

        with patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", side_effect=Exception("Deadlock detected during delete")), \
             patch.object(ingest_document_task, "retry", mock_retry):

            ingest_document_task.request.retries = 2
            with pytest.raises(Retry):
                ingest_document_task("retry-doc-del", "Text content.")

            mock_retry.assert_called_once()
            _, kwargs = mock_retry.call_args
            # Exponential backoff at retries=2: 2 ** (2 + 1) = 8s
            assert kwargs.get("countdown") == 8

    def test_worker_retry_exponential_backoff_progression(self, mock_embedder):
        """Validates that ingest_document_task invokes self.retry with exponential countdown 2**(r+1)."""
        mock_retry = MagicMock(side_effect=Retry("Retry triggered"))

        for retries_attempt in [0, 1, 2]:
            mock_retry.reset_mock()
            with patch("app.worker.embedder.encode", mock_embedder.encode), \
                 patch("app.worker.delete_chunks_by_source_id", return_value=0), \
                 patch("app.worker.insert_chunks_batch", side_effect=Exception("Database transient error")), \
                 patch.object(ingest_document_task, "retry", mock_retry):

                ingest_document_task.request.retries = retries_attempt
                with pytest.raises(Retry):
                    ingest_document_task(f"retry-progression-{retries_attempt}", "Some document text content.")

                mock_retry.assert_called_once()
                _, kwargs = mock_retry.call_args
                expected_countdown = 2 ** (retries_attempt + 1)
                assert kwargs.get("countdown") == expected_countdown

    def test_idempotent_ingestion_pre_delete_failure_prevents_insert(self, mock_embedder):
        """If pre-delete fails, insertion must never occur to prevent corrupt state."""
        mock_retry = MagicMock(side_effect=Retry("Retry triggered"))
        mock_insert = MagicMock()

        with patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", side_effect=Exception("Delete failed")), \
             patch("app.worker.insert_chunks_batch", mock_insert), \
             patch.object(ingest_document_task, "retry", mock_retry):

            ingest_document_task.request.retries = 0
            with pytest.raises(Retry):
                ingest_document_task("doc-predelete-fail", "Text for ingestion.")

            mock_insert.assert_not_called()

    def test_idempotent_ingestion_lifecycle(self, mock_embedder):
        """Guarantees delete_chunks_by_source_id is executed strictly BEFORE insert_chunks_batch."""
        execution_order = []

        def tracking_delete(source_id: str) -> int:
            execution_order.append(("delete", source_id))
            return 3

        def tracking_insert(source_id: str, chunks: List[str], embeddings: Any) -> int:
            execution_order.append(("insert", source_id, len(chunks)))
            return len(chunks)

        with patch("app.worker.embedder.encode", mock_embedder.encode), \
             patch("app.worker.delete_chunks_by_source_id", side_effect=tracking_delete), \
             patch("app.worker.insert_chunks_batch", side_effect=tracking_insert):

            source_id = "doc-idempotency-spec"
            result = ingest_document_task(source_id, "Sentence one. Sentence two.")

            assert result["status"] == "success"
            assert len(execution_order) == 2
            assert execution_order[0] == ("delete", source_id)
            assert execution_order[1][0] == "insert"
            assert execution_order[1][1] == source_id
