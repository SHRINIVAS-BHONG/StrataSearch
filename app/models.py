"""
Pydantic v2 data models for StrataSearch API and Retrieval Engine.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentRecord(BaseModel):
    """
    Metadata record for an ingested document in the StrataSearch document registry.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    doc_id: str = Field(..., description="Unique document UUID or identifier")
    filename: str = Field(..., description="Original filename or resource title")
    source_type: str = Field(..., description="Source type ('pdf', 'docx', 'txt', 'md', 'csv', 'url')")
    file_size_bytes: int = Field(default=0, ge=0, description="File size in bytes")
    chunk_count: int = Field(default=0, ge=0, description="Total indexed text chunks")
    status: str = Field(default="queued", description="Processing status: 'queued', 'processing', 'indexed', 'failed'")
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")
    created_at: Optional[str] = Field(default=None, description="ISO-8601 creation timestamp")

    @field_validator("created_at", mode="before")
    @classmethod
    def _serialize_created_at(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)


class DocumentListResponse(BaseModel):
    """
    Response model for document listing and corpus-wide statistics.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    documents: List[DocumentRecord] = Field(default_factory=list, description="List of registered documents")
    total_documents: int = Field(default=0, ge=0, description="Total registered documents count")
    total_chunks: int = Field(default=0, ge=0, description="Total chunks across all documents")
    total_size_bytes: int = Field(default=0, ge=0, description="Total storage in bytes across documents")


class UrlIngestRequest(BaseModel):
    """
    Request model for web URL crawling and ingestion.
    """
    model_config = ConfigDict(extra="ignore")

    url: str = Field(..., min_length=1, description="Target web page URL to crawl and ingest")
    title: Optional[str] = Field(default=None, description="Optional custom document title")


class IngestRequest(BaseModel):
    """
    Request model for document ingestion (legacy).
    """
    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(
        ...,
        description="Unique identifier for the source document or entity"
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Raw text content to be chunked, embedded, and indexed"
    )


class SearchRequest(BaseModel):
    """
    Request model for hybrid retrieval and search ablation queries.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(
        ...,
        min_length=1,
        description="User search query string",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of search results to return",
    )
    mode: str = Field(
        default="hybrid",
        description="Search mode: 'hybrid' (RRF fusion), 'dense' (HNSW cosine), or 'sparse' (GIN full-text)",
    )
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="Smoothing constant / rank penalty parameter for RRF fusion",
    )
    source_filter: Optional[str] = Field(
        default=None,
        description="Optional filter by doc_id, source_id, or filename",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"hybrid", "dense", "sparse"}
        if normalized not in allowed:
            raise ValueError(f"mode must be one of {allowed}, got '{value}'")
        return normalized


class SearchResultItem(BaseModel):
    """
    Individual search result item with rank tracking, relevance score, and highlighting metadata.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True, populate_by_name=True)

    chunk_id: int = Field(default=0, description="Unique chunk primary key ID")
    source_id: str = Field(..., description="Source document identifier")
    chunk_index: int = Field(default=0, description="0-based chunk sequence index within document")
    content: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(default=0.0, description="Reciprocal Rank Fusion or similarity score")
    dense_rank: Optional[int] = Field(
        default=None,
        description="1-based rank from dense vector retrieval (None if not in dense top candidates)",
    )
    sparse_rank: Optional[int] = Field(
        default=None,
        description="1-based rank from sparse full-text retrieval (None if not in sparse top candidates)",
    )
    doc_id: Optional[str] = Field(default=None, description="Parent document UUID or identifier")
    filename: Optional[str] = Field(default=None, description="Original source document filename")
    matched_terms: List[str] = Field(
        default_factory=list,
        description="Keywords matched from the search query in this chunk",
    )

    # Backward compatibility aliases for legacy callers and tests
    id: Optional[int] = Field(default=None, description="Legacy alias for chunk_id")
    rrf_score: Optional[float] = Field(default=None, description="Legacy alias for score")

    @model_validator(mode="before")
    @classmethod
    def _sync_compat_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync chunk_id and id
            if "chunk_id" not in data and "id" in data:
                data["chunk_id"] = data["id"]
            elif "id" not in data and "chunk_id" in data:
                data["id"] = data["chunk_id"]
            elif "chunk_id" in data and "id" in data:
                if data["chunk_id"] is None and data["id"] is not None:
                    data["chunk_id"] = data["id"]
                elif data["id"] is None and data["chunk_id"] is not None:
                    data["id"] = data["chunk_id"]

            # Sync score and rrf_score
            if "score" not in data and "rrf_score" in data:
                data["score"] = data["rrf_score"]
            elif "rrf_score" not in data and "score" in data:
                data["rrf_score"] = data["score"]
            elif "score" in data and "rrf_score" in data:
                if data["score"] is None and data["rrf_score"] is not None:
                    data["score"] = data["rrf_score"]
                elif data["rrf_score"] is None and data["score"] is not None:
                    data["rrf_score"] = data["score"]
        return data

    @model_validator(mode="after")
    def _finalize_compat(self) -> "SearchResultItem":
        if self.id is None:
            self.id = self.chunk_id
        if self.rrf_score is None:
            self.rrf_score = self.score
        return self


class SearchResponse(BaseModel):
    """
    Response model for search queries including latency, caching, and execution strategy metadata.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    query: str = Field(default="", description="Search query string")
    results: List[SearchResultItem] = Field(default_factory=list, description="Ranked list of search results")
    total_hits: int = Field(default=0, description="Total matching hits")
    latency_ms: float = Field(..., ge=0.0, description="Execution latency in milliseconds")
    cache_hit: bool = Field(default=False, description="True if response was served from cache")
    strategy_used: str = Field(default="hybrid", description="Retrieval strategy executed ('hybrid', 'dense', 'sparse')")

    # Backward compatibility for legacy tests and API endpoints
    mode: Optional[str] = Field(default=None, description="Retrieval mode (legacy alias for strategy_used)")

    @model_validator(mode="before")
    @classmethod
    def _sync_response_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "strategy_used" not in data and "mode" in data:
                data["strategy_used"] = data["mode"]
            elif "mode" not in data and "strategy_used" in data:
                data["mode"] = data["strategy_used"]
            if "total_hits" not in data and "results" in data:
                try:
                    data["total_hits"] = len(data["results"])
                except Exception:
                    pass
        return data

    @model_validator(mode="after")
    def _finalize_response(self) -> "SearchResponse":
        if self.mode is None:
            self.mode = self.strategy_used
        if not self.total_hits and self.results:
            self.total_hits = len(self.results)
        return self


class SystemMetricsResponse(BaseModel):
    """
    Response model for system health, telemetry, and subsystem statuses.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    status: str = Field(default="operational", description="Overall system health status")
    subsystems: Dict[str, Any] = Field(default_factory=dict, description="Subsystem health statuses")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="System telemetry and performance metrics")


__all__ = [
    "DocumentRecord",
    "DocumentListResponse",
    "UrlIngestRequest",
    "IngestRequest",
    "SearchRequest",
    "SearchResultItem",
    "SearchResponse",
    "SystemMetricsResponse",
]
