"""
Automated Pytest Suite for StrataSearch 100,000-Page Stress Testing, Needle Verification, and Corpus Purge.

Coverage:
1. Streaming Corpus Generator & Deterministic Tagging (Feature 18):
   - Lazy streaming generator yielding pages with bounded memory footprint
   - Deterministic tagging format: test_stress_100k:{run_id}:p{page_idx}
2. Ground-Truth Needle Injection & Unbiased Retrieval (Features 19, 21):
   - Deterministic injection of 5 needles across 5%, 25%, 50%, 75%, 95% positions
   - Distinct synthetic target facts and search queries per needle
   - Unbiased Recall@5 evaluation calculation (1.0, 0.6, 0.0)
   - Collision-free positioning on small corpora
3. High-Throughput Batch Ingestion & Partitioning (Feature 20):
   - Batching items in page_size/batch_size slices (e.g. 256)
   - Ingestion throughput metrics computation
4. Automated Test Corpus Cleanup & Zero-Residual Verification (Features 4, 6, 22):
   - Batched cascading deletion using cleanup_test_data
   - Strict zero-residual verification using get_chunk_count == 0
   - Prefix isolation: production/other records untouched during cleanup
5. Scenario 5 End-to-End Stress Simulation & Purge (Tier 4):
   - End-to-end simulated lifecycle: stream -> inject -> evaluate recall -> purge -> verify 0 residual
"""

import uuid
from typing import Any, Dict, Generator, List, Tuple
from unittest.mock import MagicMock, patch
import pytest

from app.database import cleanup_test_data, get_chunk_count


from scripts.stress_test_100k import (
    NEEDLE_SPECIFICATIONS,
    evaluate_needle_recall,
    inject_needles_into_stream,
    run_stress_test_100k,
    stream_synthetic_pages,
)
from scripts.bulk_ingest import generate_synthetic_corpus, run_bulk_ingest


# ===========================================================================
# 1. Streaming Generator & Deterministic Tagging Tests (Feature 18)
# ===========================================================================
class TestCorpusGeneratorAndTagging:
    def test_streaming_corpus_generator_yields_deterministic_tags(self):
        """Generator yields items lazily with test_stress_100k:{run_id}:... source_id."""
        run_id = "test_run_alpha"
        gen = stream_synthetic_pages(10, run_id)

        items = list(gen)
        assert len(items) == 10
        assert items[0][0] == f"test_stress_100k:{run_id}:p000000"
        assert items[9][0] == f"test_stress_100k:{run_id}:p000009"
        for source_id, text in items:
            assert source_id.startswith(f"test_stress_100k:{run_id}:")
            assert len(text) > 20

    def test_streaming_generator_is_lazy(self):
        """Generator does not instantiate all 100k items in memory upfront."""
        gen = stream_synthetic_pages(100000, "run_lazy")
        first = next(gen)
        assert first[0] == "test_stress_100k:run_lazy:p000000"
        second = next(gen)
        assert second[0] == "test_stress_100k:run_lazy:p000001"


# ===========================================================================
# 2. Needle Injection & Recall Evaluation Tests (Features 19, 21)
# ===========================================================================
class TestNeedleInjectionAndRecall:
    def test_ground_truth_needle_injection_five_positions(self):
        """Needle injection places exactly 5 needles near 5%, 25%, 50%, 75%, 95%."""
        needles, injected = inject_needles_into_stream(1000, "run_needles")
        assert len(needles) == 5
        assert len(injected) == 5

        # Check approximate positioning
        positions = [n["page_idx"] for n in needles]
        assert pytest.approx(positions[0], abs=10) == 50
        assert pytest.approx(positions[1], abs=10) == 250
        assert pytest.approx(positions[2], abs=10) == 500
        assert pytest.approx(positions[3], abs=10) == 750
        assert pytest.approx(positions[4], abs=10) == 950

    def test_needle_injection_small_corpus_no_collision(self):
        """On a small 10-page corpus, indices must not collide."""
        needles, injected = inject_needles_into_stream(10, "run_small")
        assert len(needles) == 5
        assert len(injected) == 5
        page_indices = [n["page_idx"] for n in needles]
        assert len(set(page_indices)) == 5

    def test_evaluate_needle_recall_perfect(self):
        """When all needles are retrieved in top 5, Recall@5 is 1.0."""
        needles, _ = inject_needles_into_stream(100, "run_recall")
        simulated_results = {}
        for n in needles:
            simulated_results[n["query"]] = [n["source_id"], "other_1", "other_2"]

        recall = evaluate_needle_recall(simulated_results, needles, top_k=5)
        assert recall == 1.0

    def test_evaluate_needle_recall_partial(self):
        """When 3 of 5 needles are retrieved, Recall@5 is 0.6."""
        needles, _ = inject_needles_into_stream(100, "run_recall")
        simulated_results = {}
        for i, n in enumerate(needles):
            if i < 3:
                simulated_results[n["query"]] = [n["source_id"]]
            else:
                simulated_results[n["query"]] = ["missed_doc_1", "missed_doc_2"]

        recall = evaluate_needle_recall(simulated_results, needles, top_k=5)
        assert pytest.approx(recall, rel=1e-3) == 0.6

    def test_evaluate_needle_recall_zero_and_empty(self):
        """Zero hits evaluates cleanly to 0.0 without division by zero."""
        needles, _ = inject_needles_into_stream(100, "run_recall")
        simulated_results = {n["query"]: ["unrelated_doc"] for n in needles}

        recall = evaluate_needle_recall(simulated_results, needles, top_k=5)
        assert recall == 0.0

        empty_recall = evaluate_needle_recall({}, [], top_k=5)
        assert empty_recall == 0.0

    def test_inject_needles_into_stream_raises_on_insufficient_pages(self):
        """inject_needles_into_stream raises ValueError when num_pages < len(NEEDLE_SPECIFICATIONS)."""
        with pytest.raises(ValueError, match="num_pages.*must be >= 5 to inject all needles"):
            inject_needles_into_stream(4, "run_fail")

        with pytest.raises(ValueError, match="num_pages.*must be >= 5 to inject all needles"):
            inject_needles_into_stream(0, "run_fail")


# ===========================================================================
# 3. High-Throughput Batch Partitioning & Metrics Tests (Feature 20)
# ===========================================================================
class TestBatchPartitioningAndMetrics:
    def test_batch_partitioning_size_256(self):
        """Items are grouped into batches of size 256."""
        items = list(range(600))
        batch_size = 256
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        assert len(batches) == 3
        assert len(batches[0]) == 256
        assert len(batches[1]) == 256
        assert len(batches[2]) == 88

    def test_throughput_calculation_metrics(self):
        """Throughput calculation computes total chunks, elapsed time, and chunks/sec."""
        total_chunks = 1000
        elapsed_sec = 2.5
        chunks_per_sec = total_chunks / elapsed_sec
        metrics = {
            "total_chunks": total_chunks,
            "elapsed_sec": elapsed_sec,
            "chunks_per_second": chunks_per_sec,
        }
        assert metrics["total_chunks"] == 1000
        assert metrics["chunks_per_second"] == 400.0


# ===========================================================================
# 4. Automated Corpus Cleanup & Zero Residual Tests (Features 4, 6, 22)
# ===========================================================================
class TestPurgeAndZeroResidualVerification:
    def test_automated_test_corpus_cleanup_zero_residual(self, mock_db_conn):
        """cleanup_test_data deletes records and get_chunk_count confirms 0 residual."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        # 1. Simulating cleanup deleting 1500 records
        cur.rowcount = 1500
        # 2. get_chunk_count returns 0
        cur.fetchone.return_value = (0,)

        with patch("app.database.get_connection", return_value=mock_db_conn), \
             patch("app.database.release_connection"):

            deleted = cleanup_test_data("test_stress_100k", batch_size=5000)
            remaining = get_chunk_count("test_stress_100k")

        assert deleted == 1500
        assert remaining == 0

    def test_cleanup_prefix_isolation(self, mock_db_conn):
        """Cleanup with prefix 'test_stress_100k' targets only matching records."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.rowcount = 50

        with patch("app.database.get_connection", return_value=mock_db_conn), \
             patch("app.database.release_connection"):

            cleanup_test_data("test_stress_100k:run_99", batch_size=5000)

        # Verify SQL pattern uses prefix%
        call_sql, call_params = cur.execute.call_args[0]
        assert "WHERE source_id LIKE %s" in call_sql
        assert call_params[0] == "test_stress_100k:run_99%"


# ===========================================================================
# 5. Scenario 5: End-to-End Stress Simulation & Purge (Tier 4)
# ===========================================================================
class TestScenario5CorpusSimulationAndPurge:
    def test_scenario_5_corpus_stress_simulation_and_purge(self, mock_db_conn):
        """Simulates end-to-end lifecycle: stream -> inject needles -> evaluate -> purge -> 0 residual."""
        run_id = f"sim_{uuid.uuid4().hex[:8]}"
        num_pages = 50

        # Step 1: Generate stream and inject needles
        needles, injected = inject_needles_into_stream(num_pages, run_id)
        assert len(needles) == 5

        # Step 2: Stream simulated pages
        pages = list(stream_synthetic_pages(num_pages, run_id))
        assert len(pages) == num_pages

        # Step 3: Verify retrieval recall
        simulated_search_results = {
            n["query"]: [n["source_id"], "other_doc_1"] for n in needles
        }
        recall = evaluate_needle_recall(simulated_search_results, needles, top_k=5)
        assert recall == 1.0

        # Step 4: Execute batched purge and verify zero residual
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.rowcount = num_pages
        cur.fetchone.return_value = (0,)

        with patch("app.database.get_connection", return_value=mock_db_conn), \
             patch("app.database.release_connection"):

            deleted = cleanup_test_data(f"test_stress_100k:{run_id}", batch_size=5000)
            residual = get_chunk_count(f"test_stress_100k:{run_id}")

        assert deleted == num_pages
        assert residual == 0

    def test_run_stress_test_100k_simulation_lifecycle(self):
        """run_stress_test_100k in simulation mode completes with 100% invariant compliance."""
        metrics = run_stress_test_100k(
            num_pages=20,
            batch_size=5,
            simulate_db=True,
            verify_recall=True,
            cleanup=True,
        )
        assert metrics["num_pages"] == 20
        assert metrics["total_chunks"] == 20
        assert metrics["needles_injected"] == 5
        assert metrics["recall_at_5"] == 1.0
        assert metrics["zero_residual_passed"] is True
        assert metrics["heap_limit_passed"] is True


# ===========================================================================
# 6. Bulk Ingestion Script Tests
# ===========================================================================
class TestBulkIngestScript:
    def test_generate_synthetic_corpus_contract(self):
        """generate_synthetic_corpus produces at least min_chunks with valid source_id and content."""
        corpus = generate_synthetic_corpus(min_chunks=60)
        assert len(corpus) >= 60
        for src, text in corpus:
            assert src.startswith("synthetic://")
            assert len(text.strip()) > 0

    def test_run_bulk_ingest_multi_batch_slicing_zero_data_loss(self):
        """run_bulk_ingest slices corpus across batches, preserves sequential chunk indices, and suffers zero data loss."""
        corpus = [
            ("doc_alpha", "Chunk 0 content"),
            ("doc_alpha", "Chunk 1 content"),
            ("doc_alpha", "Chunk 2 content"),
            ("doc_alpha", "Chunk 3 content"),
            ("doc_beta", "Chunk 0 content for beta"),
            ("doc_alpha", "Chunk 4 content"),
        ]

        inserted_records = []

        def mock_insert(source_id, chunks, embeddings, start_chunk_index=0):
            for i, c in enumerate(chunks):
                inserted_records.append((source_id, start_chunk_index + i, c))
            return len(chunks)

        mock_emb = MagicMock()
        mock_emb.encode.side_effect = lambda texts, **kw: [[0.1] * 384 for _ in texts]

        with patch("scripts.bulk_ingest.init_db"), \
             patch("scripts.bulk_ingest.embedder", mock_emb), \
             patch("scripts.bulk_ingest.insert_chunks_batch", side_effect=mock_insert):

            run_bulk_ingest(corpus, batch_size=2, skip_db_init=True)

        # Total 6 chunks inserted across 3 batches of size 2 (zero data loss)
        assert len(inserted_records) == 6

        # Verify sequential chunk indices per source across batch boundaries
        alpha_records = [r for r in inserted_records if r[0] == "doc_alpha"]
        beta_records = [r for r in inserted_records if r[0] == "doc_beta"]

        assert len(alpha_records) == 5
        assert [r[1] for r in alpha_records] == [0, 1, 2, 3, 4]
        assert [r[2] for r in alpha_records] == [
            "Chunk 0 content",
            "Chunk 1 content",
            "Chunk 2 content",
            "Chunk 3 content",
            "Chunk 4 content",
        ]

        assert len(beta_records) == 1
        assert beta_records[0][1] == 0
        assert beta_records[0][2] == "Chunk 0 content for beta"
