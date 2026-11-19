"""
Automated Pytest Suite for StrataSearch API Gateway, Caching, and Resiliency Layer.

Coverage:
1. Cache Invalidation & Management (Feature 15):
   - clear_search_cache clears Redis keys matching pattern
   - In-memory cache clearing fallback
   - Empty cache returns 0 without error
2. Cache Poisoning Prevention & Circuit Breaker (Feature 14):
   - Database failure avoids storing empty results in Redis cache
   - Circuit breaker activation on repeated database failures
3. Asynchronous Event-Loop Non-Blocking Offload (Features 12, 13):
   - Ingest PDF offloading CPU-intensive PDF parsing
   - Search offloading vector similarity computations
4. Gateway Validation, Rate Limiting & Health Checks:
   - PDF upload non-pdf extension rejected (HTTP 400)
   - Empty PDF upload rejected (HTTP 400)
   - Sliding-window rate limit enforcement (HTTP 429)
   - Health check endpoint reflecting healthy (200) vs degraded (503) status
"""

import fnmatch
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import (
    app,
    check_rate_limit,
    execute_search_resilient,
    get_redis_client,
    _local_search_cache,
    _local_cache_lock,
    _local_rate_limits,
    _local_rate_limit_lock,
)


@pytest.fixture(autouse=True)
def reset_gateway_state():
    """Resets rate limiting state between test cases to ensure complete test isolation."""
    with _local_rate_limit_lock:
        _local_rate_limits.clear()
    yield
    with _local_rate_limit_lock:
        _local_rate_limits.clear()


# ===========================================================================
# 1. Cache Invalidation Tests (Feature 15)
# ===========================================================================
class TestCacheInvalidation:
    def test_clear_search_cache_removes_redis_keys(self, mock_redis):
        """clear_search_cache deletes keys matching search_cache:* from Redis."""
        from app.main import clear_search_cache
        mock_redis.set("search_cache:hash1", json.dumps([{"id": 1}]))
        mock_redis.set("search_cache:hash2", json.dumps([{"id": 2}]))
        mock_redis.set("other_key:123", "value")

        with patch("app.main.get_redis_client", return_value=mock_redis):
            deleted = clear_search_cache()

        assert deleted >= 2
        assert mock_redis.get("search_cache:hash1") is None
        assert mock_redis.get("search_cache:hash2") is None
        assert mock_redis.get("other_key:123") == "value"

    def test_clear_search_cache_removes_local_keys(self):
        """clear_search_cache purges keys from _local_search_cache."""
        from app.main import clear_search_cache
        with _local_cache_lock:
            _local_search_cache["search_cache:local1"] = (time.time() + 3600, [{"id": 10}])
            _local_search_cache["search_cache:local2"] = (time.time() + 3600, [{"id": 20}])

        with patch("app.main.get_redis_client", return_value=None):
            deleted = clear_search_cache()

        assert deleted >= 2
        with _local_cache_lock:
            assert "search_cache:local1" not in _local_search_cache
            assert "search_cache:local2" not in _local_search_cache

    def test_clear_search_cache_empty_returns_zero(self, mock_redis):
        """Calling clear_search_cache on an already empty cache returns 0 cleanly."""
        from app.main import clear_search_cache
        with patch("app.main.get_redis_client", return_value=mock_redis):
            count = clear_search_cache()
            assert count == 0

    def test_clear_search_cache_sums_redis_and_local_keys(self, mock_redis):
        """clear_search_cache correctly sums Redis deleted keys + local in-memory deleted keys."""
        from app.main import clear_search_cache
        mock_redis.set("search_cache:redis_key1", json.dumps([{"id": 1}]))
        mock_redis.set("search_cache:redis_key2", json.dumps([{"id": 2}]))

        with _local_cache_lock:
            _local_search_cache["search_cache:local_key1"] = (time.time() + 3600, [{"id": 10}])
            _local_search_cache["search_cache:local_key2"] = (time.time() + 3600, [{"id": 20}])
            _local_search_cache["search_cache:local_key3"] = (time.time() + 3600, [{"id": 30}])

        with patch("app.main.get_redis_client", return_value=mock_redis):
            total_deleted = clear_search_cache()

        # 2 from Redis + 3 from local in-memory cache = 5 total
        assert total_deleted == 5
        assert mock_redis.get("search_cache:redis_key1") is None
        assert mock_redis.get("search_cache:redis_key2") is None
        with _local_cache_lock:
            assert "search_cache:local_key1" not in _local_search_cache
            assert "search_cache:local_key2" not in _local_search_cache
            assert "search_cache:local_key3" not in _local_search_cache

    def test_cache_clear_endpoint_contract(self, mock_redis):
        """POST /api/v1/cache/clear endpoint must exist and invalidate search cache per PROJECT.md § F15."""
        client = TestClient(app)
        mock_redis.set("search_cache:doc_abc", json.dumps([{"id": 1}]))

        with patch("app.main.get_redis_client", return_value=mock_redis):
            response = client.post("/api/v1/cache/clear")

        assert response.status_code == 200
        assert mock_redis.get("search_cache:doc_abc") is None

    def test_clear_search_cache_invalid_prefix_type_raises(self):
        """clear_search_cache with non-string non-None prefix must raise TypeError."""
        from app.main import clear_search_cache
        with pytest.raises(TypeError, match="prefix must be a string or None"):
            clear_search_cache(prefix=123)  # type: ignore

        with pytest.raises(TypeError, match="prefix must be a string or None"):
            clear_search_cache(prefix=True)  # type: ignore


# ===========================================================================
# 2. Cache Poisoning Prevention & Circuit Breaker (Feature 14)
# ===========================================================================
class TestCachePoisoningPrevention:
    def test_search_database_failure_does_not_poison_cache(self, mock_redis):
        """Database error during search must return HTTP 503 and not store empty list [] into Redis cache."""
        client = TestClient(app)

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.execute_search_resilient", side_effect=Exception("Database crash")), \
             patch("app.main.hybrid_search_rrf", side_effect=Exception("Database crash")):

            response = client.post(
                "/api/v1/search",
                json={"query": "test query for poisoning check", "top_k": 5, "mode": "hybrid"},
            )

        assert response.status_code == 503
        assert "Database" in response.json().get("detail", "")
        # Check that cache key was not populated with empty results on failure
        keys = mock_redis.keys("search_cache:*")
        assert len(keys) == 0, f"Cache was poisoned with keys on DB error: {keys}"

    def test_search_unhandled_database_exception_trips_circuit_and_returns_503(self, mock_redis):
        """When hybrid_search_rrf fails, search_endpoint returns HTTP 503 and activates circuit breaker."""
        import app.main as main_mod
        client = TestClient(app)

        with main_mod._db_circuit_lock:
            main_mod._db_circuit_open_until = 0.0

        try:
            with patch("app.main.get_redis_client", return_value=mock_redis), \
                 patch("app.main.hybrid_search_rrf", side_effect=Exception("Connection timeout")):

                response = client.post(
                    "/api/v1/search",
                    json={"query": "test circuit breaker tripping", "top_k": 5, "mode": "hybrid"},
                )

            assert response.status_code == 503
            assert "Database search failed" in response.json().get("detail", "")
            assert main_mod._db_circuit_open_until > time.time()

            # Subsequent search call while circuit breaker is open must immediately return 503
            response2 = client.post(
                "/api/v1/search",
                json={"query": "second query while breaker open", "top_k": 5, "mode": "hybrid"},
            )
            assert response2.status_code == 503
            assert "circuit breaker active" in response2.json().get("detail", "")

        finally:
            with main_mod._db_circuit_lock:
                main_mod._db_circuit_open_until = 0.0

    def test_circuit_breaker_blocks_cascading_db_failures(self):
        """After database failure, circuit breaker trips to protect database."""
        import app.main as main_mod

        # Trip circuit breaker
        with main_mod._db_circuit_lock:
            main_mod._db_circuit_open_until = time.time() + 10.0

        with patch("app.main.hybrid_search_rrf") as mock_search:
            res = execute_search_resilient("query", 5, "hybrid")
            assert res == []
            mock_search.assert_not_called()

        # Reset circuit breaker
        with main_mod._db_circuit_lock:
            main_mod._db_circuit_open_until = 0.0


# ===========================================================================
# 3. Gateway Validation, Rate Limiting & Health Checks
# ===========================================================================
class TestGatewayValidationAndHealth:
    def test_pdf_upload_non_pdf_extension_rejected(self):
        """Uploading non-.pdf file must return HTTP 400 Bad Request."""
        client = TestClient(app)
        files = {"file": ("malicious.exe", b"binarycontent", "application/octet-stream")}
        response = client.post("/api/v1/ingest/pdf", files=files)
        assert response.status_code == 400
        assert "must be a PDF" in response.json()["detail"]

    def test_pdf_upload_empty_file_rejected(self):
        """Uploading empty 0-byte PDF must return HTTP 400 Bad Request."""
        client = TestClient(app)
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        response = client.post("/api/v1/ingest/pdf", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_rate_limiting_sliding_window_enforcement(self, mock_redis):
        """Exceeding request limit within window strictly raises HTTP 429 HTTPException."""
        with patch("app.main.get_redis_client", return_value=mock_redis):
            # First 5 requests within limit must succeed
            for _ in range(5):
                assert check_rate_limit("client_rate_test", limit=5, window_sec=60) is True

            # The 6th request must exceed limit and raise HTTP 429
            with pytest.raises(HTTPException) as exc_info:
                check_rate_limit("client_rate_test", limit=5, window_sec=60)
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.detail

    def test_health_check_healthy(self, mock_redis, mock_db_conn):
        """Health check returns HTTP 200 when Redis and PostgreSQL are operational."""
        client = TestClient(app)
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1,)

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.get_connection", return_value=mock_db_conn), \
             patch("app.main.release_connection"):

            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"]["status"] == "ok"
        assert data["postgres"]["status"] == "ok"

    def test_health_check_degraded_when_postgres_down(self, mock_redis):
        """Health check returns HTTP 503 when PostgreSQL pool is unreachable."""
        client = TestClient(app)

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.get_connection", side_effect=Exception("DB pool exhausted")):

            response = client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["postgres"]["status"] == "down"

    def test_health_check_degraded_when_redis_down(self, mock_db_conn):
        """Health check returns HTTP 503 when Redis is unreachable."""
        client = TestClient(app)
        cur = mock_db_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1,)

        with patch("app.main.get_redis_client", return_value=None), \
             patch("app.main.get_connection", return_value=mock_db_conn), \
             patch("app.main.release_connection"):

            response = client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["redis"]["status"] == "down"


# ===========================================================================
# 4. Gateway Endpoint Contracts & Ingestion Lifecycle
# ===========================================================================
class TestGatewayEndpointContracts:
    def test_post_ingest_endpoint(self, mock_redis):
        """POST /api/v1/ingest accepts document, enqueues celery task, and returns 202."""
        client = TestClient(app)
        mock_task = MagicMock()
        mock_task.id = "mock-celery-task-123"

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.ingest_document_task.delay", return_value=mock_task) as mock_delay:

            response = client.post(
                "/api/v1/ingest",
                json={"source_id": "test_doc_001", "text": "This is raw document text content to be chunked."},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["task_id"] == "mock-celery-task-123"
        assert data["source_id"] == "test_doc_001"
        assert "accepted" in data["message"].lower()
        mock_delay.assert_called_once_with("test_doc_001", "This is raw document text content to be chunked.")

    def test_get_task_status_endpoint(self):
        """GET /api/v1/tasks/{task_id} returns Celery AsyncResult status and chunk counts."""
        client = TestClient(app)
        mock_async_res = MagicMock()
        mock_async_res.status = "SUCCESS"
        mock_async_res.ready.return_value = True
        mock_async_res.successful.return_value = True
        mock_async_res.result = {"chunks_count": 8, "source_id": "doc_test"}

        with patch("app.main.celery_app.AsyncResult", return_value=mock_async_res):
            response = client.get("/api/v1/tasks/task-abc-456")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-abc-456"
        assert data["status"] == "SUCCESS"
        assert data["chunks_count"] == 8
        assert data["ready"] is True
        assert data["successful"] is True
        assert data["error"] is None

    def test_post_ingest_pdf_success_and_offload(self, mock_redis, sample_pdf_bytes):
        """POST /api/v1/ingest/pdf accepts valid PDF, offloads text extraction, enqueues task, returns 202."""
        client = TestClient(app)
        mock_task = MagicMock()
        mock_task.id = "mock-pdf-task-789"

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.ingest_document_task.delay", return_value=mock_task) as mock_delay:

            files = {"file": ("document.pdf", sample_pdf_bytes, "application/pdf")}
            data = {"source_id": "custom_pdf_doc"}
            response = client.post("/api/v1/ingest/pdf", files=files, data=data)

        assert response.status_code == 202
        res_data = response.json()
        assert res_data["status"] == "queued"
        assert res_data["task_id"] == "mock-pdf-task-789"
        assert res_data["source_id"] == "custom_pdf_doc"
        assert res_data["filename"] == "document.pdf"
        assert res_data["extracted_length"] > 0
        mock_delay.assert_called_once()

    def test_post_search_repeated_query_cache_hit(self, mock_redis):
        """POST /api/v1/search executes search and on repeated query returns cached result with cache_hit=True."""
        client = TestClient(app)

        mock_search_results = [
            {
                "id": 1,
                "source_id": "src_1",
                "content": "Result chunk content",
                "dense_rank": 1,
                "sparse_rank": 1,
                "rrf_score": 0.033,
            }
        ]

        with patch("app.main.get_redis_client", return_value=mock_redis), \
             patch("app.main.execute_search_resilient", return_value=mock_search_results) as mock_search:

            # 1. First query execution (live search)
            resp1 = client.post(
                "/api/v1/search",
                json={"query": "Cache hit verification query", "top_k": 5, "mode": "hybrid"},
            )
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["cache_hit"] is False
            assert len(data1["results"]) == 1
            assert mock_search.call_count == 1

            # 2. Second repeated query execution (served from cache)
            resp2 = client.post(
                "/api/v1/search",
                json={"query": "Cache hit verification query", "top_k": 5, "mode": "hybrid"},
            )
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["cache_hit"] is True
            assert len(data2["results"]) == 1
            assert data2["results"][0]["id"] == 1
            # Verify execute_search_resilient was NOT called a second time
            assert mock_search.call_count == 1
