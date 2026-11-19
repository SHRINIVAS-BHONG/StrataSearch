"""
Automated Pytest Suite for StrataSearch Hybrid Retrieval and RRF Engine.

Coverage:
1. RRF Parameter Validation & Score Fusion (Feature 17):
   - Standard k values (k=60, k=20, k=1)
   - Zero or negative k validation / guarding against ZeroDivisionError
   - Single-modality dominance vs joint-modality balance
   - Empty dense/sparse rankings
   - Descending score sort order
2. Sparse Search Query Robustness (Feature 16):
   - Complex conversational query syntax
   - Punctuation and special characters
   - Unclosed quotation handling
3. Search Execution & Modal Ablation (Features 1, 13):
   - Mode 'hybrid': executes both dense vector and sparse lexical queries
   - Mode 'dense': executes only pgvector cosine distance query
   - Mode 'sparse': executes only full-text tsvector query
   - Unsupported search mode raises ValueError
   - Guaranteed connection release on database error (try...finally)
   - Empty and whitespace queries return empty list
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from app.models import SearchResultItem
from app.search import _prepare_vector_param, compute_rrf, hybrid_search_rrf


# ===========================================================================
# 1. RRF Parameter Validation & Math Verification (Feature 17)
# ===========================================================================
class TestRRFParameterValidation:
    def test_compute_rrf_standard_k_values(self):
        """Standard smoothing constants (60, 20, 1) fuse scores correctly."""
        dense = {101: 1, 102: 2}
        sparse = {101: 2, 102: 1}

        for k in [60, 20, 1]:
            scores = compute_rrf(dense, sparse, rrf_k=k)
            assert len(scores) == 2
            # Symmetric ranks (1,2) and (2,1) must produce identical scores
            assert pytest.approx(scores[101], rel=1e-5) == scores[102]
            assert scores[101] > 0.0

    def test_compute_rrf_zero_or_negative_k_guard(self):
        """Zero or negative rrf_k must strictly raise ValueError per PROJECT.md § F17."""
        with pytest.raises(ValueError, match="rrf_k must be an integer >= 1"):
            compute_rrf({1: 1}, {1: 1}, rrf_k=0)

        with pytest.raises(ValueError, match="rrf_k must be an integer >= 1"):
            compute_rrf({1: 1}, {1: 1}, rrf_k=-1)

        with pytest.raises(ValueError, match="rrf_k must be an integer >= 1"):
            compute_rrf({1: 1}, {1: 1}, rrf_k=-5)

        with pytest.raises(ValueError, match="rrf_k must be an integer >= 1"):
            compute_rrf({1: 1}, {}, rrf_k=-10)

    def test_compute_rrf_invalid_type_k_guard(self):
        """Non-integer rrf_k must raise TypeError or ValueError per interface contract."""
        with pytest.raises((TypeError, ValueError)):
            compute_rrf({1: 1}, {1: 1}, rrf_k="invalid_k")  # type: ignore

        with pytest.raises((TypeError, ValueError)):
            compute_rrf({1: 1}, {1: 1}, rrf_k=None)  # type: ignore

    def test_compute_rrf_invalid_rank_values_guard(self):
        """Candidate rank values < 1, boolean, or non-integer must raise ValueError to prevent ZeroDivisionError."""
        with pytest.raises(ValueError, match="Document rank must be an integer >= 1"):
            compute_rrf({1: -60}, {}, rrf_k=60)

        with pytest.raises(ValueError, match="Document rank must be an integer >= 1"):
            compute_rrf({}, {1: -60}, rrf_k=60)

        with pytest.raises(ValueError, match="Document rank must be an integer >= 1"):
            compute_rrf({1: 0}, {}, rrf_k=60)

        with pytest.raises(ValueError, match="Document rank must be an integer >= 1"):
            compute_rrf({1: True}, {}, rrf_k=60)

    def test_compute_rrf_descending_sort_order(self):
        """Fused dictionary must be strictly ordered descending by score."""
        dense = {1: 1, 2: 2, 3: 3, 4: 4}
        sparse = {1: 1, 2: 3, 3: 2, 4: 5}

        scores = compute_rrf(dense, sparse, rrf_k=60)
        items = list(scores.items())
        for i in range(len(items) - 1):
            assert items[i][1] >= items[i + 1][1]

    def test_compute_rrf_empty_rankings(self):
        """Empty dense or sparse rankings return empty or single-modality scores."""
        assert compute_rrf({}, {}, rrf_k=60) == {}

        dense_only = compute_rrf({1: 1}, {}, rrf_k=60)
        assert len(dense_only) == 1
        assert pytest.approx(dense_only[1], rel=1e-5) == 1.0 / 61.0

        sparse_only = compute_rrf({}, {2: 1}, rrf_k=60)
        assert len(sparse_only) == 1
        assert pytest.approx(sparse_only[2], rel=1e-5) == 1.0 / 61.0

    def test_prepare_vector_param_conversions(self):
        """_prepare_vector_param properly handles numpy arrays, lists, and tuples."""
        list_vec = [0.1, -0.2, 0.3]
        arr1 = _prepare_vector_param(list_vec)
        assert isinstance(arr1, np.ndarray)
        assert arr1.dtype == np.float32

        tuple_vec = (1.0, 2.0, 3.0)
        arr2 = _prepare_vector_param(tuple_vec)
        assert isinstance(arr2, np.ndarray)
        assert arr2.dtype == np.float32

        np_vec = np.array([0.5, 0.6], dtype=np.float64)
        arr3 = _prepare_vector_param(np_vec)
        assert arr3.dtype == np.float32


# ===========================================================================
# 2. Sparse Search Query Robustness Tests (Feature 16)
# ===========================================================================
class TestSparseSearchQueryRobustness:
    def test_sparse_search_conversational_query_syntax(self, mock_db_conn):
        """Conversational queries containing boolean logic and quotes execute cleanly."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            (10, "doc_1", "PostgreSQL database with pgvector and full-text search.")
        ]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection") as mock_rel:
            results = hybrid_search_rrf(
                query='PostgreSQL OR pgvector NOT "unwanted legacy"',
                top_k=5,
                mode="sparse",
            )

        assert len(results) == 1
        assert results[0]["id"] == 10
        mock_rel.assert_called_once_with(mock_db_conn)

    def test_sparse_search_special_punctuation(self, mock_db_conn):
        """Queries containing heavy punctuation do not crash the sparse query builder."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection"):
            results = hybrid_search_rrf(
                query="Testing special chars: !!! @@@ $$$ %%% ^^^ &&& *** ( )",
                top_k=5,
                mode="sparse",
            )
        assert isinstance(results, list)

    def test_sparse_search_unclosed_quotes(self, mock_db_conn):
        """Unclosed quotes in queries do not crash the search engine."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection"):
            results = hybrid_search_rrf(
                query='"unclosed quotation query without closing quote',
                top_k=5,
                mode="sparse",
            )
        assert isinstance(results, list)

    def test_sparse_search_rollback_on_websearch_failure_before_fallback(self, mock_db_conn):
        """When websearch_to_tsquery throws an exception, conn.rollback() is invoked before plainto_tsquery runs."""
        import psycopg2
        call_order = []

        def mock_rollback():
            call_order.append("rollback")

        mock_db_conn.rollback.side_effect = mock_rollback

        cur = mock_db_conn.cursor.return_value.__enter__.return_value

        def mock_execute(sql, params):
            if "websearch_to_tsquery" in sql:
                call_order.append("execute_websearch")
                raise psycopg2.DatabaseError("syntax error in tsquery from websearch")
            elif "plainto_tsquery" in sql:
                call_order.append("execute_plainto")
            else:
                call_order.append("execute_other")

        cur.execute.side_effect = mock_execute
        cur.fetchall.return_value = [(42, "doc_fallback", "Fallback content match")]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection"):
            results = hybrid_search_rrf(
                query="problematic websearch query",
                top_k=5,
                mode="sparse",
            )

        assert len(results) == 1
        assert results[0]["id"] == 42
        assert results[0]["source_id"] == "doc_fallback"
        # Assert call order: websearch execution -> rollback -> plainto fallback execution
        assert call_order == ["execute_websearch", "rollback", "execute_plainto"]


# ===========================================================================
# 3. Hybrid Search Execution & Modal Ablation Tests (Features 1, 13)
# ===========================================================================
class TestHybridSearchAblation:
    def test_hybrid_search_empty_query_returns_empty_list(self):
        """Empty or whitespace queries return empty list immediately without acquiring DB conn."""
        with patch("app.search.get_connection") as mock_get_conn:
            assert hybrid_search_rrf("") == []
            assert hybrid_search_rrf("   \n  ") == []
            mock_get_conn.assert_not_called()

    def test_hybrid_search_mode_hybrid_executes_dense_and_sparse(self, mock_db_conn, mock_embedder):
        """Mode 'hybrid' executes both vector cosine distance and tsvector queries."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        # Dense returns doc 1, sparse returns doc 1 and doc 2
        cur.fetchall.side_effect = [
            [(1, "doc_alpha", "Content chunk one")],
            [(1, "doc_alpha", "Content chunk one"), (2, "doc_beta", "Content chunk two")],
        ]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection") as mock_rel, \
             patch("app.search.embedder.encode", mock_embedder.encode):

            results = hybrid_search_rrf(
                query="Distributed semantic vector search",
                top_k=5,
                mode="hybrid",
            )

        assert len(results) == 2
        assert cur.execute.call_count == 2
        mock_rel.assert_called_once_with(mock_db_conn)
        # Results match SearchResultItem schema
        assert results[0]["id"] == 1
        assert "rrf_score" in results[0]
        assert results[0]["dense_rank"] == 1
        assert results[0]["sparse_rank"] == 1

    def test_hybrid_search_mode_dense_only(self, mock_db_conn, mock_embedder):
        """Mode 'dense' executes only vector query and bypasses sparse query."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            (10, "source_dense", "Dense content vector match")
        ]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection") as mock_rel, \
             patch("app.search.embedder.encode", mock_embedder.encode):

            results = hybrid_search_rrf(
                query="Dense search query",
                top_k=5,
                mode="dense",
            )

        assert len(results) == 1
        assert cur.execute.call_count == 1
        assert "embedding <=>" in cur.execute.call_args[0][0]
        assert results[0]["dense_rank"] == 1
        assert results[0]["sparse_rank"] is None
        mock_rel.assert_called_once_with(mock_db_conn)

    def test_hybrid_search_mode_sparse_only(self, mock_db_conn):
        """Mode 'sparse' executes only tsvector query and bypasses embedder."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            (20, "source_sparse", "Sparse lexeme keyword match")
        ]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection") as mock_rel, \
             patch("app.search.embedder.encode") as mock_encode:

            results = hybrid_search_rrf(
                query="Sparse keyword search",
                top_k=5,
                mode="sparse",
            )

        assert len(results) == 1
        assert cur.execute.call_count == 1
        assert "tsv @@" in cur.execute.call_args[0][0]
        mock_encode.assert_not_called()
        assert results[0]["sparse_rank"] == 1
        assert results[0]["dense_rank"] is None
        mock_rel.assert_called_once_with(mock_db_conn)

    def test_hybrid_search_unsupported_mode_raises_value_error(self):
        """Invalid search modes raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported search mode"):
            hybrid_search_rrf("query", mode="invalid_mode")

    def test_hybrid_search_connection_release_guaranteed_on_error(self, mock_db_conn):
        """Database errors during search guarantee connection is released back to pool."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.execute.side_effect = Exception("Database connection reset by peer")

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection") as mock_rel:

            with pytest.raises(Exception, match="Database connection reset"):
                hybrid_search_rrf("Test query", mode="sparse")

        mock_rel.assert_called_once_with(mock_db_conn)

    def test_hybrid_search_top_k_bounds(self, mock_db_conn):
        """top_k restricts the number of results returned."""
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [
            (i, f"doc_{i}", f"Content chunk {i}") for i in range(1, 10)
        ]

        with patch("app.search.get_connection", return_value=mock_db_conn), \
             patch("app.search.release_connection"):

            results = hybrid_search_rrf("Large candidate pool", top_k=3, mode="sparse")

        assert len(results) == 3
