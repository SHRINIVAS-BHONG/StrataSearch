"""
Shared Isolated Mock Fixtures for StrataSearch Test Suite.

Provides fast, high-fidelity, deterministic mocks for:
- PostgreSQL Connection Pool (psycopg2.pool.ThreadedConnectionPool, conn, cursor)
- Redis Client and Pipeline (redis.Redis, sorted sets, sliding-window rate limiting, key expiration)
- SentenceTransformer Embedder (deterministic 384-dimensional float32 unit vectors)
- Synthetic document and PDF byte generators
"""

import io
import fnmatch
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import psycopg2.extensions as ext


@pytest.fixture
def mock_cursor():
    """Mock database cursor with standard return values."""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = (0,)
    cursor.rowcount = 0
    return cursor


@pytest.fixture
def mock_db_conn(mock_cursor):
    """Mock psycopg2 database connection with idle transaction state."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = mock_cursor
    conn.closed = False
    conn.status = 0
    conn.get_transaction_status.return_value = ext.TRANSACTION_STATUS_IDLE
    return conn


@pytest.fixture
def mock_db_pool(mock_db_conn):
    """Mock ThreadedConnectionPool providing mock_db_conn."""
    pool = MagicMock()
    pool.closed = False
    pool.getconn.return_value = mock_db_conn
    return pool


@pytest.fixture(autouse=True)
def default_db_isolation(monkeypatch, mock_db_conn, mock_db_pool):
    """
    Guarantees isolated unit execution without live PostgreSQL connectivity per TEST_READY.md.
    Provides mock database connection by default unless overridden by test-specific patch.
    """
    monkeypatch.setattr("app.database.get_pool", lambda *a, **kw: mock_db_pool)
    monkeypatch.setattr("app.database.get_connection", lambda *a, **kw: mock_db_conn)
    monkeypatch.setattr("app.search.get_connection", lambda *a, **kw: mock_db_conn)


class InMemoryRedis:
    """High-fidelity in-memory Redis mock supporting string, zset, and pipeline operations."""

    def __init__(self):
        self.data: Dict[str, str] = {}
        self.zsets: Dict[str, Dict[str, float]] = {}
        self.ttls: Dict[str, int] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> Optional[str]:
        return self.data.get(key)

    def set(self, key: str, value: str) -> bool:
        self.data[key] = str(value)
        return True

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self.data[key] = str(value)
        self.ttls[key] = ttl
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.data:
                del self.data[k]
                count += 1
            if k in self.zsets:
                del self.zsets[k]
                count += 1
        return count

    def incr(self, key: str) -> int:
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val

    def keys(self, pattern: str = "*") -> List[str]:
        all_keys = list(self.data.keys()) + list(self.zsets.keys())
        return [k for k in set(all_keys) if fnmatch.fnmatch(k, pattern)]

    def pipeline(self):
        return MockRedisPipeline(self)


class MockRedisPipeline:
    """Mock pipeline supporting sliding-window operations and command buffering."""

    def __init__(self, r: InMemoryRedis):
        self.r = r
        self.commands: List[tuple] = []
        self._zrem_result = 0
        self._zcard_result = 0

    def zremrangebyscore(self, key: str, min_s: float, max_s: float):
        zset = self.r.zsets.get(key, {})
        to_del = [m for m, s in zset.items() if min_s <= s <= max_s]
        for m in to_del:
            del zset[m]
        self._zrem_result = len(to_del)
        self.commands.append(("zrem", key, min_s, max_s))
        return self

    def zcard(self, key: str):
        zset = self.r.zsets.get(key, {})
        self._zcard_result = len(zset)
        self.commands.append(("zcard", key))
        return self

    def zadd(self, key: str, mapping: Dict[str, float]):
        if key not in self.r.zsets:
            self.r.zsets[key] = {}
        self.r.zsets[key].update(mapping)
        self.commands.append(("zadd", key, mapping))
        return self

    def expire(self, key: str, ttl: int):
        self.r.ttls[key] = ttl
        self.commands.append(("expire", key, ttl))
        return self

    def execute(self) -> List[Any]:
        # Typical pipeline returns results for [zremrangebyscore, zcard, zadd, expire]
        return [self._zrem_result, self._zcard_result, 1, True]


@pytest.fixture
def mock_redis():
    """Provides isolated InMemoryRedis instance."""
    return InMemoryRedis()


class MockSentenceTransformer:
    """Fast deterministic embedder returning normalized 384-dimensional unit vectors."""

    def encode(
        self,
        sentences: Any,
        normalize_embeddings: bool = True,
        **kwargs: Any,
    ) -> np.ndarray:
        is_single = isinstance(sentences, str)
        items = [sentences] if is_single else list(sentences)
        count = len(items)

        # Generate deterministic float32 vectors based on content length / hash
        vectors = np.zeros((count, 384), dtype=np.float32)
        for i, text in enumerate(items):
            # Non-zero first component guaranteed for unit norm
            vectors[i, 0] = 1.0
            # Small perturbation based on string length to distinguish chunks
            if len(text) > 0:
                vectors[i, 1] = float(len(text) % 100) / 1000.0

        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = vectors / norms

        return vectors[0] if is_single else vectors


@pytest.fixture
def mock_embedder():
    """Provides MockSentenceTransformer."""
    return MockSentenceTransformer()


@pytest.fixture
def sample_pdf_bytes():
    """Generates valid minimal in-memory PDF bytes containing digital text."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(
        (50, 100),
        "StrataSearch Distributed Hybrid RAG Engine Technical Specification Document.",
        fontsize=12,
    )
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
