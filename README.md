# StrataSearch — Enterprise Hybrid Retrieval & Document Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?logo=docker&logoColor=white)](https://www.docker.com)

StrataSearch is a production-grade, client-ready **Enterprise Hybrid Retrieval & Document Intelligence Platform**. It unifies dense semantic vector retrieval (pgvector HNSW with 384-dimensional cosine distance) and sparse lexical retrieval (PostgreSQL GIN tsvector full-text search) using Reciprocal Rank Fusion (RRF), delivering sub-15ms cached query responses, multi-format document ingestion, and cascading lifecycle management.

---

## Architecture Overview

StrataSearch is engineered across five decoupled tiers:

```text
                                 +-----------------------------------------------+
                                 |            Web Browser / API Client           |
                                 +-----------------------+-----------------------+
                                                         |
                                                         v
                                 +-----------------------------------------------+
                                 |         StrataSearch FastAPI Gateway          |
                                 |   (Lifespan Warmup, Rate Limiter, Cache)     |
                                 +-----------+-----------------------+-----------+
                                             |                       |
               [POST /api/v1/documents/*]    |                       |    [POST /api/v1/search]
               (Asynchronous Ingestion Job)  |                       |    (Hybrid RRF Retrieval)
                                             v                       v
                         +-----------------------+       +-----------------------+
                         | Redis Queue / In-Proc |       |   Redis SHA-256 Cache |
                         | (Single-Node Fallback)|       |   (In-Memory LRU)     |
                         +-----------+-----------+       +-----------+-----------+
                                     |                               | (On Cache Miss)
                                     v                               v
                         +-----------------------+       +-----------------------+
                         | Celery Ingestion Pool |       |   Hybrid RRF Engine   |
                         | - PyMuPDF / Tesseract |       | - Dense: pgvector     |
                         | - python-docx / bs4   |       | - Sparse: GIN tsvector|
                         | - all-MiniLM-L6-v2    |       | - RRF: 1 / (k + rank) |
                         +-----------+-----------+       +-----------+-----------+
                                     |                               |
                                     +---------------+---------------+
                                                     |
                                                     v
                                 +-----------------------------------------------+
                                 |            PostgreSQL 16 + pgvector           |
                                 |  - documents metadata table                   |
                                 |  - document_chunks table (ON DELETE CASCADE)  |
                                 |  - HNSW Index (Cosine Distance, m=16, ef=64)  |
                                 |  - GIN Index (to_tsvector English)            |
                                 +-----------------------------------------------+
```

---

## Core Capabilities

- **Zero-Framework "Strata Obsidian" UI**: Hand-crafted, modern dark-mode frontend built with pure HTML5, vanilla CSS3 custom properties, and native ES6 JavaScript (`fetch`, `async/await`). Zero external CSS/JS frameworks (no Tailwind CDN, no React/Vue/npm overhead).
- **Multi-Format Document Parsing**:
  - **PDF**: Fast extraction via PyMuPDF with automatic 200-DPI pytesseract OCR fallback for scanned documents (<30 digital characters).
  - **DOCX**: Complete paragraph and table text extraction via `python-docx`.
  - **Plaintext & Data**: UTF-8 decoding and NUL-byte (`\x00`) sanitization for `.txt`, `.md`, and `.csv`.
  - **Web Articles & Docs**: Automated HTTP web scraping via `httpx` + `BeautifulSoup4` with boilerplate stripping (`<nav>`, `<footer>`, `<script>`, `<style>`).
- **Pre-Warmed Hybrid RRF Search**: Combines pgvector HNSW cosine ranking and PostgreSQL GIN full-text ranking using Reciprocal Rank Fusion:
  $$RRF(d) = \frac{1}{k + \text{rank}_{\text{dense}}(d)} + \frac{1}{k + \text{rank}_{\text{sparse}}(d)}$$
- **Document-Scoped Retrieval**: Filter search results to specific documents (`doc_id` or filename) while maintaining sub-15ms execution latency.
- **Cascading Metadata & Vector Purge**: Removing a document from the registry automatically purges all associated vector chunks and embeddings via SQL `ON DELETE CASCADE`.
- **Dual-Mode Deployment**: Supports both enterprise distributed multi-container deployment (Celery workers + Redis) and zero-dependency single-node cloud deployment (`SINGLE_NODE_MODE=true` on Render Starter).
- **Sub-2-Second Container Cold Start**: Docker image pre-bakes `all-MiniLM-L6-v2` neural model weights into image layers during build, eliminating network download overhead during container initialization.

---

## REST API Reference

All endpoints are versioned under `/api/v1` and document schemas are strictly validated via Pydantic v2:

| HTTP Method | Endpoint | Description | Request Body / Params | Response |
|---|---|---|---|---|
| `GET` | `/` | Web dashboard or service metadata | Header: `Accept: text/html` or `application/json` | HTML / JSON |
| `GET` | `/ui` | Direct access to StrataSearch workbench | None | `text/html` |
| `POST` | `/api/v1/documents/upload` | Upload & enqueue multiple documents (up to 25MB each) | Multipart form `files` (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`) | `202 Accepted` (List of Document Records) |
| `POST` | `/api/v1/documents/url` | Scrape, sanitize, and index web page | JSON: `{"url": "https://...", "title": "Optional"}` | `202 Accepted` (Document Record) |
| `GET` | `/api/v1/documents` | List document registry with corpus statistics | None | `200 OK` (`documents`, `total_documents`, `total_chunks`, `total_size_bytes`) |
| `DELETE` | `/api/v1/documents/{doc_id}` | Delete document and cascade vector purge | Path parameter: `doc_id` | `200 OK` (`{"status": "deleted", "doc_id": "..."}`) |
| `POST` | `/api/v1/search` | Execute hybrid RRF, dense, or sparse search | JSON: `{"query": "...", "top_k": 5, "mode": "hybrid", "rrf_k": 60, "source_filter": null}` | `200 OK` (`results`, `latency_ms`, `cache_hit`, `strategy_used`) |
| `DELETE` | `/api/v1/cache` | Invalidate active query search caches | None | `200 OK` (`{"status": "cleared", "keys_purged": N}`) |
| `GET` | `/api/v1/health` | Live diagnostic probe of all subsystems | None | `200 OK` (`{"status": "healthy", "subsystems": {...}}`) |

---

## Deployment Guides

### Option 1: Multi-Container Production Stack (Docker Compose)

The multi-container stack runs PostgreSQL 16 with pgvector, Redis 7, the FastAPI Gateway, and the Celery worker pool:

```bash
# 1. Clone repository
git clone https://github.com/your-org/stratasearch.git
cd stratasearch

# 2. Build and launch all 4 containers
docker compose up --build -d

# 3. Verify health status
curl -f http://localhost:8000/api/v1/health
```

The stack exposes:
- **Web UI & REST API Gateway**: `http://localhost:8000`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`
- **PostgreSQL 16 (pgvector)**: `localhost:5432`
- **Redis Cache & Message Broker**: `localhost:6379`

### Option 2: Single-Service Cloud Deployment (Render Blueprint)

Deploy StrataSearch on Render with a single web service and managed PostgreSQL (pgvector). The single-node engine handles document ingestion synchronously and falls back to thread-safe in-memory LRU caching, removing the need for an external Redis instance:

1. Connect your repository to **Render** (`https://dashboard.render.com`).
2. Select **New Blueprint Instance** and reference the repository.
3. Render automatically reads `render.yaml`, provisions the `stratasearch-db` database, sets `SINGLE_NODE_MODE=true`, and launches the web container with built-in health probes at `/api/v1/health`.

### Option 3: Local Development (Bare Metal)

#### Prerequisites
- Python 3.11+
- PostgreSQL 16 with `pgvector` extension enabled
- Redis 7.0+ (optional when `SINGLE_NODE_MODE=true`)
- Tesseract OCR (installed and available on system path)

#### Setup Steps
```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Configure environment variables (.env)
export DATABASE_URL="postgresql://postgres:password@localhost:5432/hybrid_rag"
export REDIS_URL="redis://localhost:6379/0"
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
export SINGLE_NODE_MODE="true"  # Set to "false" if running Celery worker

# 4. Launch FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Cold Start & Performance Optimization

In containerized deployments, downloading neural model weights during container boot introduces 15–30 second cold-start delays. StrataSearch's multi-stage `Dockerfile` executes a pre-caching stage during the build phase:

```dockerfile
# Builder stage caches weights into /root/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Runner stage copies pre-cached weights into final minimal image
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
```

This guarantees sub-2-second container initialization and immediate readiness for live inference without requiring external internet connectivity at runtime.

---

## Verification & Testing

StrataSearch includes an automated test suite verifying database operations, OCR fallback, multi-format parsing, hybrid search math, API gateways, and packaging specifications:

```bash
# Execute full test suite
python -m pytest tests -v
```

All 155+ unit, integration, and contract tests run with mock isolation, allowing execution in developer environments without live external database daemons.

---

## License

Enterprise Proprietary Commercial License. All rights reserved.
