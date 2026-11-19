"""
Ingestion, OCR, Semantic Chunking, and Embedding module for StrataSearch.

Features:
- Windows fallback configuration for Tesseract OCR.
- Pre-warmed Resilient singleton SentenceTransformer embedder with SHA-256 fallback.
- extract_text_from_pdf with 200-DPI pytesseract OCR fallback for scanned/low-text pages (<30 chars).
- extract_text_from_docx with python-docx for paragraphs and table cell contents.
- extract_text_from_text_file for TXT, MD, CSV with UTF-8 / latin-1 decoding and NUL-byte sanitization.
- extract_text_from_url with httpx + BeautifulSoup4 stripping nav, footer, script, style, header, noscript.
- extract_document_text unified multi-format dispatcher.
- semantic_chunk_text splitting cleanly on sentence boundaries with sliding-window overlap.
"""

import io
import logging
import os
import re
from typing import Any, List, Optional, Union
from urllib.parse import urlparse

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF fallback
import numpy as np
import pytesseract
from PIL import Image

try:
    from app.config import EMBEDDING_MODEL, TESSERACT_WIN_PATH
except ImportError:
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    TESSERACT_WIN_PATH = os.getenv("TESSERACT_WIN_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 0. Text Sanitization (NUL Byte Stripping for PostgreSQL Compatibility)
# ---------------------------------------------------------------------------
def sanitize_text(text: Any) -> str:
    """
    Sanitizes input text by removing null bytes (\\x00) for PostgreSQL compatibility.
    Handles None, non-string objects, and empty strings gracefully.

    Args:
        text: Input string or object to sanitize.

    Returns:
        Sanitized string stripped of all null bytes.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return ""
    return text.replace("\x00", "")


# ---------------------------------------------------------------------------
# 1. Automatic Windows fallback for Tesseract OCR
# ---------------------------------------------------------------------------
def configure_tesseract() -> None:
    """Configures pytesseract command path, prioritizing config path on Windows."""
    if os.name == "nt":
        candidate_paths = [
            TESSERACT_WIN_PATH,
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in candidate_paths:
            if path and os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info("Configured Tesseract binary path at: %s", path)
                return
        logger.debug("Tesseract binary not found at default Windows paths; using system PATH.")


configure_tesseract()


# ---------------------------------------------------------------------------
# 2. Resilient Singleton Embedder with Preloading
# ---------------------------------------------------------------------------
class ResilientSentenceTransformer:
    """
    Singleton wrapper for SentenceTransformer embedding model.
    Preloads the model on startup for sub-2-second cold starts, while providing
    graceful fallback to deterministic normalized pseudo-embeddings if PyTorch/HuggingFace
    dependencies or model weights are unavailable during tests or offline environments.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL, eager_load: bool = True):
        self.model_name = model_name
        self._model: Optional[Any] = None
        self._model_load_attempted = False
        if eager_load:
            self.preload()

    def preload(self) -> Optional[Any]:
        """Eagerly loads the SentenceTransformer model if not yet attempted."""
        return self._get_model()

    def _get_model(self) -> Optional[Any]:
        if not self._model_load_attempted:
            self._model_load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading SentenceTransformer model '%s'...", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info("SentenceTransformer model '%s' loaded successfully.", self.model_name)
            except Exception as e:
                logger.warning(
                    "SentenceTransformer could not be initialized (%s). Using fallback embedding generator.",
                    e,
                )
                self._model = None
        return self._model

    def encode(
        self,
        sentences: Union[str, List[str]],
        normalize_embeddings: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Generates 384-dimensional dense vector embeddings.
        Returns normalized float arrays matching SentenceTransformer signature.
        """
        model = self._get_model()
        if model is not None:
            return model.encode(sentences, normalize_embeddings=normalize_embeddings, **kwargs)

        # Fallback implementation: 384-dimensional normalized deterministic vectors
        import hashlib

        is_single = isinstance(sentences, str)
        items = [sentences] if is_single else list(sentences)
        results = []
        for text in items:
            raw_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
            # Expand sha256 (32 bytes) to 384 floats (12 blocks)
            buffer = raw_hash * 12
            arr = (np.frombuffer(buffer, dtype=np.uint8)[:384].astype(np.float32) - 128.0)
            if normalize_embeddings:
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
            results.append(arr)

        arr_out = np.array(results, dtype=np.float32)
        return arr_out[0] if is_single else arr_out

    def __getattr__(self, name: str) -> Any:
        model = self._get_model()
        if model is not None:
            return getattr(model, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Singleton instance exported for use across the application (eagerly preloaded)
embedder = ResilientSentenceTransformer(EMBEDDING_MODEL, eager_load=True)


# ---------------------------------------------------------------------------
# 3. Multi-Format Document Extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text from PDF bytes using PyMuPDF (fitz).
    Automatically falls back to 200-DPI pytesseract OCR whenever a page has <30
    characters of digital text (e.g. scanned documents or graphical pages).
    All extracted text is sanitized to eliminate NUL bytes.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted and OCR'd full document text, sanitized of NUL bytes.
    """
    if not pdf_bytes:
        return ""

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as err:
        logger.warning("Failed to open PDF stream: %s", err)
        return ""

    pages_text: List[str] = []

    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            raw_digital = page.get_text()
            digital_text = sanitize_text(raw_digital).strip()

            if len(digital_text) >= 30:
                pages_text.append(digital_text)
            else:
                logger.debug(
                    "Page %d has only %d characters. Triggering 200-DPI OCR fallback.",
                    page_index + 1,
                    len(digital_text),
                )
                # Render page at 200 DPI (standard PDF DPI is 72; 200 / 72 ~= 2.7778)
                zoom = 200.0 / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix)

                ocr_text = ""
                try:
                    # Convert fitz pixmap to PIL Image
                    image_bytes = pixmap.tobytes("png")
                    image = Image.open(io.BytesIO(image_bytes))
                    raw_ocr = pytesseract.image_to_string(image)
                    ocr_text = sanitize_text(raw_ocr).strip()
                except Exception as ocr_err:
                    logger.warning("OCR processing failed for page %d: %s", page_index + 1, ocr_err)

                # Use OCR text if recovered, otherwise retain any digital text
                page_result = ocr_text if len(ocr_text) >= len(digital_text) else digital_text
                if page_result:
                    pages_text.append(page_result)
    finally:
        doc.close()

    full_text = "\n\n".join(pages_text).strip()
    return sanitize_text(full_text)


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """
    Extracts text from DOCX file bytes using python-docx.
    Extracts all paragraph text and table cell content.
    Sanitizes extracted text to eliminate NUL bytes.

    Args:
        docx_bytes: Raw bytes of the DOCX document.

    Returns:
        Extracted and sanitized document text.
    """
    if not docx_bytes:
        return ""

    try:
        import docx
    except ImportError:
        logger.error("python-docx is not installed.")
        return ""

    try:
        doc = docx.Document(io.BytesIO(docx_bytes))
    except Exception as err:
        logger.warning("Failed to parse DOCX bytes: %s", err)
        return ""

    text_parts: List[str] = []

    # Paragraphs
    for p in doc.paragraphs:
        p_text = sanitize_text(p.text).strip()
        if p_text:
            text_parts.append(p_text)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            seen_cells = set()
            row_texts: List[str] = []
            for cell in row.cells:
                # Deduplicate merged cells sharing the same underlying XML element
                cell_id = id(cell._tc)
                if cell_id not in seen_cells:
                    seen_cells.add(cell_id)
                    c_text = sanitize_text(cell.text).strip()
                    if c_text:
                        row_texts.append(c_text)
            if row_texts:
                text_parts.append(" | ".join(row_texts))

    full_text = "\n\n".join(text_parts).strip()
    return sanitize_text(full_text)


def extract_text_from_text_file(text_bytes: bytes) -> str:
    """
    Extracts text from plain text formats (TXT, MD, CSV) with UTF-8 decoding,
    automatic fallback to latin-1 or character replacement, and NUL-byte sanitization.

    Args:
        text_bytes: Raw bytes from the text file.

    Returns:
        Decoded, sanitized text content.
    """
    if not text_bytes:
        return ""

    if isinstance(text_bytes, str):
        return sanitize_text(text_bytes).strip()

    if not isinstance(text_bytes, (bytes, bytearray)):
        try:
            text_bytes = bytes(text_bytes)
        except Exception:
            return ""

    try:
        decoded = text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = text_bytes.decode("latin-1")
        except Exception:
            decoded = text_bytes.decode("utf-8", errors="replace")

    return sanitize_text(decoded).strip()


def extract_text_from_url(url: str, timeout: float = 10.0) -> str:
    """
    Fetches web page content using httpx and extracts clean readable text using BeautifulSoup4.
    Decomposes <nav>, <footer>, <script>, <style>, <header>, and <noscript> elements.
    Validates URL scheme (strictly http:// or https://).

    Args:
        url: Web URL to fetch and parse.
        timeout: Request timeout in seconds (default 10.0).

    Returns:
        Extracted and sanitized web text content.

    Raises:
        ValueError: If the URL or scheme is invalid.
        httpx.HTTPError: If the HTTP request fails.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL: URL must be a non-empty string.")

    clean_url = url.strip()
    parsed = urlparse(clean_url)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL scheme or format: '{url}'. Only 'http://' and 'https://' are supported.")

    import httpx
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "StrataSearch/1.0 (Enterprise Document Retrieval)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        resp = client.get(clean_url, headers=headers)
        resp.raise_for_status()
        html_text = resp.text

    soup = BeautifulSoup(html_text, "html.parser")

    # Decompose boilerplate and non-text elements
    for element in soup(["nav", "footer", "script", "style", "header", "noscript"]):
        element.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = "\n\n".join(lines).strip()
    return sanitize_text(full_text)


def extract_document_text(
    source_type: str,
    content: bytes = b"",
    url: Optional[str] = None,
) -> str:
    """
    Unified extraction dispatcher routing to the format-specific extractor
    based on source_type ('pdf', 'docx', 'txt', 'md', 'csv', 'url').

    Args:
        source_type: Source type identifier or file extension.
        content: Raw document bytes (optional if source_type='url').
        url: Optional target URL for web ingestion.

    Returns:
        Extracted, cleaned, and sanitized text string.
    """
    norm_type = (source_type or "").lower().strip().lstrip(".")

    if norm_type == "pdf":
        return extract_text_from_pdf(content or b"")
    elif norm_type in ("docx", "doc"):
        return extract_text_from_docx(content or b"")
    elif norm_type in ("url", "web", "http", "https", "html"):
        target_url = url
        if not target_url and content:
            try:
                target_url = content.decode("utf-8", errors="ignore").strip()
            except Exception:
                pass
        if not target_url:
            raise ValueError("URL must be provided when source_type is 'url'")
        return extract_text_from_url(target_url)
    elif norm_type in ("txt", "text", "md", "markdown", "csv"):
        return extract_text_from_text_file(content or b"")
    else:
        # Fallback to text file decoder
        return extract_text_from_text_file(content or b"")


# ---------------------------------------------------------------------------
# 4. Semantic Chunking with Sliding-Window Overlap
# ---------------------------------------------------------------------------
def semantic_chunk_text(
    text: str,
    max_words: int = 180,
    overlap_words: int = 30,
) -> List[str]:
    """
    Splits text cleanly on sentence boundaries with sliding-window overlap.
    Input text is automatically sanitized to remove NUL bytes before chunking.

    Args:
        text: Input raw text to chunk.
        max_words: Maximum word count per chunk (default 180).
        overlap_words: Target word overlap between successive chunks (default 30).

    Returns:
        List of semantically chunked text strings.
    """
    cleaned = sanitize_text(text).strip()
    if not cleaned:
        return []

    # Split text into sentences using punctuation boundaries (. ! ?) and paragraph breaks
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", cleaned)
    sentences: List[str] = []

    for raw in raw_sentences:
        s = raw.strip()
        if not s:
            continue
        words = s.split()
        if len(words) > max_words:
            # Sub-split oversized sentences that exceed max_words
            step = max(1, max_words - overlap_words)
            for start in range(0, len(words), step):
                chunk_slice = words[start : start + max_words]
                sentences.append(" ".join(chunk_slice))
        else:
            sentences.append(s)

    if not sentences:
        return []

    chunks: List[str] = []
    num_sentences = len(sentences)
    start_idx = 0

    while start_idx < num_sentences:
        current_sentences: List[str] = []
        current_words = 0
        idx = start_idx

        while idx < num_sentences:
            s_word_count = len(sentences[idx].split())
            if current_words + s_word_count > max_words and current_sentences:
                break
            current_sentences.append(sentences[idx])
            current_words += s_word_count
            idx += 1

        chunk_str = " ".join(current_sentences).strip()
        if chunk_str:
            chunks.append(chunk_str)

        if idx >= num_sentences:
            break

        # Calculate sliding-window backtrack for overlap_words
        overlap_accum = 0
        next_start = idx
        for back_idx in range(idx - 1, start_idx, -1):
            b_words = len(sentences[back_idx].split())
            if overlap_accum + b_words <= overlap_words:
                overlap_accum += b_words
                next_start = back_idx
            else:
                if overlap_accum == 0 and back_idx > start_idx:
                    next_start = back_idx
                break

        # Guarantee strict forward progression
        if next_start <= start_idx:
            next_start = start_idx + 1

        start_idx = next_start

    return chunks


__all__ = [
    "sanitize_text",
    "configure_tesseract",
    "ResilientSentenceTransformer",
    "embedder",
    "extract_text_from_pdf",
    "extract_text_from_docx",
    "extract_text_from_text_file",
    "extract_text_from_url",
    "extract_document_text",
    "semantic_chunk_text",
]
