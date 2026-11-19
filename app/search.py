"""
Hybrid Retrieval and Reciprocal Rank Fusion (RRF) Engine for StrataSearch.

This module executes:
- Dense vector retrieval using pgvector HNSW cosine distance (<=>).
- Sparse full-text retrieval using PostgreSQL GIN index with Cover Density Ranking (ts_rank_cd).
- Score fusion using Reciprocal Rank Fusion (RRF): score = sum(1.0 / (rrf_k + rank)).
- Search ablation support (mode="hybrid", mode="dense", mode="sparse").
- Scoped search filtering by document identifier / source_filter.
- Term matching extraction for highlighting in search results.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

import numpy as np

from app.database import get_connection, release_connection
from app.ingest import embedder
from app.models import SearchResultItem

logger = logging.getLogger(__name__)


def warm_up_search_engine() -> bool:
    """
    Pre-warms the search engine embedding model at application startup.
    Calls embedder.embed_query("warmup search query") to ensure PyTorch and model weights
    are pre-warmed, eliminating first-query cold-start latency.

    Returns:
        bool: True if warm-up succeeded, False otherwise.
    """
    warmup_text = "warmup search query"
    try:
        # Ensure embed_query alias exists on embedder singleton if not natively present
        if not hasattr(embedder, "embed_query") and hasattr(embedder, "encode"):
            try:
                setattr(embedder, "embed_query", getattr(embedder, "encode"))
            except Exception:
                pass

        if hasattr(embedder, "embed_query") and callable(getattr(embedder, "embed_query")):
            embedder.embed_query(warmup_text)
        elif hasattr(embedder, "encode") and callable(getattr(embedder, "encode")):
            embedder.encode(warmup_text)
        logger.info("Search engine embedding model pre-warmed successfully.")
        return True
    except Exception as exc:
        logger.warning("Search engine warm-up encountered non-fatal error: %s", exc)
        return False


def extract_matched_terms(query: str, content: str) -> List[str]:
    """
    Extracts matched query terms present in the document chunk content.
    Tokenizes the search query into significant keywords (lowercased, alphanumeric tokens,
    length >= 2) and checks for their presence in the content string.

    Args:
        query: User search query string.
        content: Text content of the retrieved chunk.

    Returns:
        List[str]: Unique list of matched terms in order of appearance in query.
    """
    if not query or not content:
        return []

    content_lower = content.lower()
    raw_tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())

    seen = set()
    matched: List[str] = []

    for token in raw_tokens:
        if len(token) < 2:
            continue
        if token in seen:
            continue
        seen.add(token)

        if token in content_lower:
            matched.append(token)

    return matched


def compute_rrf(
    dense_ranks: Dict[int, int],
    sparse_ranks: Dict[int, int],
    rrf_k: int = 60,
) -> Dict[int, float]:
    """
    Computes Reciprocal Rank Fusion (RRF) scores across dense and sparse ranking dictionaries.

    Formula:
        RRF_score(d) = sum_{m in M} (1.0 / (rrf_k + rank_m(d)))

    Args:
        dense_ranks: Mapping from document chunk id (int) to 1-based dense rank (int).
        sparse_ranks: Mapping from document chunk id (int) to 1-based sparse rank (int).
        rrf_k: Smoothing constant / rank penalty parameter (default: 60).

    Returns:
        Dict[int, float]: Dictionary mapping document chunk id to fused RRF score,
                          sorted descending by score.
    """
    if isinstance(rrf_k, bool) or not isinstance(rrf_k, int) or rrf_k < 1:
        raise ValueError("rrf_k must be an integer >= 1")

    for rank in dense_ranks.values():
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise ValueError(f"Document rank must be an integer >= 1, got {rank!r}")

    for rank in sparse_ranks.values():
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise ValueError(f"Document rank must be an integer >= 1, got {rank!r}")

    scores: Dict[int, float] = {}
    all_doc_ids = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))

    for doc_id in all_doc_ids:
        score = 0.0
        if doc_id in dense_ranks:
            score += 1.0 / (rrf_k + dense_ranks[doc_id])
        if doc_id in sparse_ranks:
            score += 1.0 / (rrf_k + sparse_ranks[doc_id])
        scores[doc_id] = score

    # Sort descending by fused RRF score
    sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
    return sorted_scores


def _prepare_vector_param(emb: Any) -> Any:
    """
    Prepares an embedding vector for pgvector parameter binding in psycopg2.

    Args:
        emb: Vector as list, tuple, torch tensor, or numpy ndarray.

    Returns:
        numpy.ndarray: 1D float32 numpy array adapted by pgvector.
    """
    if hasattr(emb, "tolist"):
        emb = emb.tolist()
    if isinstance(emb, (list, tuple)):
        return np.array(emb, dtype=np.float32)
    if isinstance(emb, np.ndarray):
        return emb.astype(np.float32)
    return emb


def hybrid_search_rrf(
    query: str,
    top_k: int = 5,
    mode: Union[str, int] = "hybrid",
    rrf_k: int = 60,
    source_filter: Optional[str] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Executes hybrid retrieval combining HNSW dense cosine search and PostgreSQL GIN full-text search,
    fused via Reciprocal Rank Fusion (RRF).

    Supports search ablation:
    - "hybrid": Retrieves top dense and sparse candidate pools, fuses with RRF.
    - "dense": Retrieves top candidates using pgvector HNSW cosine distance only.
    - "sparse": Retrieves top candidates using PostgreSQL GIN ts_rank_cd full-text search only.

    Args:
        query: User search query string.
        top_k: Maximum number of search results to return (default: 5).
        mode: Retrieval mode ('hybrid', 'dense', or 'sparse'). Defaults to 'hybrid'.
        rrf_k: RRF smoothing constant (default: 60).
        source_filter: Optional filter by doc_id, source_id, or filename.

    Returns:
        List[Dict[str, Any]]: Top `top_k` results conforming to SearchResultItem schema.
    """
    # Handle flexible parameter ordering (mode vs rrf_k)
    if isinstance(mode, int) and not isinstance(mode, bool):
        actual_rrf_k = mode
        actual_mode = kwargs.get("mode", rrf_k if isinstance(rrf_k, str) else "hybrid")
    else:
        actual_mode = mode
        actual_rrf_k = kwargs.get("rrf_k", rrf_k)

    if "source_filter" in kwargs and source_filter is None:
        source_filter = kwargs["source_filter"]

    cleaned_query = query.strip() if query else ""
    if not cleaned_query:
        return []

    top_k = max(1, int(top_k))
    if isinstance(actual_rrf_k, bool) or not isinstance(actual_rrf_k, int) or actual_rrf_k < 1:
        raise ValueError("rrf_k must be an integer >= 1")

    normalized_mode = (actual_mode or "hybrid").strip().lower()
    if normalized_mode not in {"hybrid", "dense", "sparse"}:
        raise ValueError(
            f"Unsupported search mode '{actual_mode}'. Allowed modes: 'hybrid', 'dense', 'sparse'."
        )

    clean_source_filter = source_filter.strip() if (source_filter and isinstance(source_filter, str)) else None
    if not clean_source_filter:
        clean_source_filter = None

    # 1. Generate dense query embedding if dense modality is needed
    vector_param = None
    if normalized_mode in ("hybrid", "dense"):
        raw_embedding = embedder.encode(cleaned_query, normalize_embeddings=True)
        vector_param = _prepare_vector_param(raw_embedding)

    # Candidate pool limit: retrieve larger pool for hybrid fusion to maximize overlap
    candidate_k = top_k if normalized_mode in ("dense", "sparse") else max(top_k * 4, 50)

    dense_candidates: List[tuple] = []
    sparse_candidates: List[tuple] = []

    # 2. Execute database queries with guaranteed connection release via try...finally
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 2a. Dense Retrieval via HNSW Cosine Distance (<=>)
            if normalized_mode in ("hybrid", "dense") and vector_param is not None:
                dense_query = """
                    SELECT id, source_id, content, chunk_index, doc_id
                    FROM document_chunks
                    WHERE (%s IS NULL OR source_id = %s OR doc_id = %s)
                    ORDER BY embedding <=> %s
                    LIMIT %s;
                """
                cur.execute(
                    dense_query,
                    (clean_source_filter, clean_source_filter, clean_source_filter, vector_param, candidate_k),
                )
                dense_candidates = cur.fetchall()

            # 2b. Sparse Retrieval via PostgreSQL GIN Full-Text Search (websearch_to_tsquery)
            if normalized_mode in ("hybrid", "sparse"):
                sparse_query = """
                    SELECT id, source_id, content, chunk_index, doc_id
                    FROM document_chunks
                    WHERE (%s IS NULL OR source_id = %s OR doc_id = %s)
                      AND tsv @@ websearch_to_tsquery('english', %s)
                    ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('english', %s)) DESC
                    LIMIT %s;
                """
                try:
                    cur.execute(
                        sparse_query,
                        (
                            clean_source_filter,
                            clean_source_filter,
                            clean_source_filter,
                            cleaned_query,
                            cleaned_query,
                            candidate_k,
                        ),
                    )
                    sparse_candidates = cur.fetchall()
                except Exception as sparse_err:
                    logger.warning(
                        f"websearch_to_tsquery failed for query '{cleaned_query}': {sparse_err}. "
                        "Attempting plainto_tsquery fallback."
                    )
                    conn.rollback()
                    fallback_query = """
                        SELECT id, source_id, content, chunk_index, doc_id
                        FROM document_chunks
                        WHERE (%s IS NULL OR source_id = %s OR doc_id = %s)
                          AND tsv @@ plainto_tsquery('english', %s)
                        ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', %s)) DESC
                        LIMIT %s;
                    """
                    cur.execute(
                        fallback_query,
                        (
                            clean_source_filter,
                            clean_source_filter,
                            clean_source_filter,
                            cleaned_query,
                            cleaned_query,
                            candidate_k,
                        ),
                    )
                    sparse_candidates = cur.fetchall()

    except Exception as e:
        logger.error(f"Error during search execution in mode '{normalized_mode}': {e}", exc_info=True)
        raise
    finally:
        # Crucial: Always return the acquired connection back to the ThreadedConnectionPool
        release_connection(conn)

    # 3. Track 1-based ranks and document chunk metadata
    dense_ranks: Dict[int, int] = {}
    sparse_ranks: Dict[int, int] = {}
    doc_metadata: Dict[int, Dict[str, Any]] = {}

    for rank, row in enumerate(dense_candidates, start=1):
        chunk_id = int(row[0])
        dense_ranks[chunk_id] = rank
        doc_metadata[chunk_id] = {
            "chunk_id": chunk_id,
            "source_id": str(row[1]),
            "content": str(row[2]),
            "chunk_index": int(row[3]) if len(row) > 3 and row[3] is not None else 0,
            "doc_id": str(row[4]) if len(row) > 4 and row[4] is not None else None,
            "filename": str(row[1]),
        }

    for rank, row in enumerate(sparse_candidates, start=1):
        chunk_id = int(row[0])
        sparse_ranks[chunk_id] = rank
        if chunk_id not in doc_metadata:
            doc_metadata[chunk_id] = {
                "chunk_id": chunk_id,
                "source_id": str(row[1]),
                "content": str(row[2]),
                "chunk_index": int(row[3]) if len(row) > 3 and row[3] is not None else 0,
                "doc_id": str(row[4]) if len(row) > 4 and row[4] is not None else None,
                "filename": str(row[1]),
            }

    # 4. Fuse candidate rankings with Reciprocal Rank Fusion
    fused_scores = compute_rrf(dense_ranks, sparse_ranks, rrf_k=actual_rrf_k)

    # 5. Format top_k results strictly matching SearchResultItem model
    results: List[Dict[str, Any]] = []
    for chunk_id, score in fused_scores.items():
        if chunk_id not in doc_metadata:
            continue
        meta = doc_metadata[chunk_id]
        matched = extract_matched_terms(cleaned_query, meta["content"])
        item = SearchResultItem(
            chunk_id=chunk_id,
            id=chunk_id,
            source_id=meta["source_id"],
            chunk_index=meta["chunk_index"],
            content=meta["content"],
            score=float(score),
            rrf_score=float(score),
            dense_rank=dense_ranks.get(chunk_id),
            sparse_rank=sparse_ranks.get(chunk_id),
            doc_id=meta["doc_id"],
            filename=meta["filename"],
            matched_terms=matched,
        )
        results.append(item.model_dump())
        if len(results) >= top_k:
            break

    return results


__all__ = [
    "compute_rrf",
    "extract_matched_terms",
    "hybrid_search_rrf",
    "warm_up_search_engine",
    "_prepare_vector_param",
]
