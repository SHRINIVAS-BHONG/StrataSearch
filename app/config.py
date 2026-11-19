"""
Configuration module for StrataSearch.
Centralizes environment configuration variables.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Centralized environment configuration
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/hybrid_rag",
)

REDIS_URL: str = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)

TESSERACT_WIN_PATH: str = os.getenv(
    "TESSERACT_WIN_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

DB_POOL_MINCONN: int = int(os.getenv("DB_POOL_MINCONN", "2"))
DB_POOL_MAXCONN: int = int(os.getenv("DB_POOL_MAXCONN", "20"))

SINGLE_NODE_MODE: bool = os.getenv("SINGLE_NODE_MODE", "false").lower() in ("true", "1", "yes")
MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)))

