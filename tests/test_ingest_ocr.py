"""
Automated Pytest Suite for StrataSearch Ingestion, OCR & Text Processing Layer.

Coverage:
1. Text Sanitization (Feature 7):
   - Stripping embedded NUL bytes (\x00) for PostgreSQL compatibility
   - Only-NUL byte strings
   - Normal alphanumeric strings & unicode preservation
   - Empty and whitespace inputs
2. PyMuPDF Modern Import (Feature 8):
   - Import verification as fitz and pymupdf
3. PDF Text Extraction & OCR Fallback (Feature 12):
   - Digital text extraction above 30-char threshold
   - Automatic 200-DPI pytesseract OCR fallback for scanned/low-text pages (<30 chars)
   - Empty PDF byte handling
   - OCR failure graceful degradation to digital text
   - Tesseract configuration lifecycle
4. Resilient SentenceTransformer Embedder (Feature 5):
   - 384-dimensional normalized vector generation
   - Batch encoding
   - Deterministic SHA-256 fallback when model weights unavailable
   - Unit norm verification
5. Semantic Sentence Chunking Integration:
   - Chunking sanitized texts
   - Sliding-window sentence boundary preservation
"""

from unittest.mock import patch
import numpy as np
import pytest

from app.ingest import (
    ResilientSentenceTransformer,
    configure_tesseract,
    embedder,
    extract_text_from_pdf,
    sanitize_text,
    semantic_chunk_text,
)


# ===========================================================================
# 1. Text Sanitization Tests (Feature 7)
# ===========================================================================
class TestTextSanitization:
    def test_sanitize_text_normal_string(self):
        """Normal text without NUL bytes should remain unmodified."""
        raw = "PostgreSQL pgvector hybrid retrieval engine with HNSW indexing."
        assert sanitize_text(raw) == raw

    def test_sanitize_text_strips_embedded_nul_bytes(self):
        """NUL bytes embedded inside text must be stripped cleanly."""
        raw = "PostgreSQL\x00 does\x00 not allow\x00 NUL bytes."
        expected = "PostgreSQL does not allow NUL bytes."
        assert sanitize_text(raw) == expected

    def test_sanitize_text_string_of_only_nul_bytes(self):
        """String of pure NUL bytes must reduce to empty string."""
        raw = "\x00\x00\x00\x00"
        assert sanitize_text(raw) == ""

    def test_sanitize_text_empty_and_whitespace(self):
        """Empty strings and whitespace strings must be handled safely."""
        assert sanitize_text("") == ""
        assert sanitize_text("   \n\t  ") == "   \n\t  "

    def test_sanitize_text_preserves_unicode_and_special_characters(self):
        """Preserves unicode, accents, mathematical symbols, and emojis."""
        raw = "StrataSearch Hybrid RAG \x00🚀 λ=0.75 Schrödinger's cat\x00!"
        cleaned = sanitize_text(raw)
        assert "\x00" not in cleaned
        assert "🚀" in cleaned
        assert "λ=0.75" in cleaned
        assert "Schrödinger's cat!" in cleaned

    def test_sanitize_text_none_input(self):
        """None input must safely return empty string without raising AttributeError."""
        assert sanitize_text(None) == ""

    def test_sanitize_text_non_string_types(self):
        """Non-string inputs like integers or floats must convert safely to string."""
        assert sanitize_text(12345) == "12345"
        assert sanitize_text(45.67) == "45.67"

    def test_sanitize_text_interspersed_null_bytes(self):
        """Repeated and interspersed null bytes are completely removed."""
        raw = "\x00p\x00g\x00v\x00e\x00c\x00t\x00o\x00r\x00"
        assert sanitize_text(raw) == "pgvector"


# ===========================================================================
# 2. PyMuPDF Modern Import Tests (Feature 8)
# ===========================================================================
class TestPyMuPDFImport:
    def test_pymupdf_imported_as_fitz(self):
        """Validates modern pymupdf / fitz library presence and interface."""
        import fitz
        assert hasattr(fitz, "open")
        assert hasattr(fitz, "Matrix")
        assert fitz.open is not None

    def test_configure_tesseract_safe_call(self):
        """configure_tesseract must execute without uncaught exceptions on any platform."""
        # Should execute safely without raising
        configure_tesseract()


# ===========================================================================
# 3. PDF Extraction & OCR Fallback Tests (Feature 12)
# ===========================================================================
class TestPDFExtractionAndOCRFallback:
    def test_extract_text_empty_pdf_bytes(self):
        """Passing empty bytes must return empty string immediately without error."""
        assert extract_text_from_pdf(b"") == ""

    def test_extract_text_digital_pdf_above_threshold(self, sample_pdf_bytes):
        """Pages with >=30 characters of digital text extract directly without OCR."""
        with patch("pytesseract.image_to_string") as mock_ocr:
            text = extract_text_from_pdf(sample_pdf_bytes)
            assert "StrataSearch Distributed Hybrid RAG Engine" in text
            # pytesseract should not be called since digital text >= 30 chars
            mock_ocr.assert_not_called()

    def test_extract_text_scanned_pdf_below_threshold_triggers_ocr(self):
        """Pages with <30 characters must trigger 200-DPI pytesseract OCR fallback."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        # Create a 1-page PDF with sparse text (<30 chars)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Sparse", fontsize=10)  # 6 chars < 30
        sparse_pdf_bytes = doc.write()
        doc.close()

        with patch("pytesseract.image_to_string", return_value="OCR Recovered Full Page Text Content") as mock_ocr:
            text = extract_text_from_pdf(sparse_pdf_bytes)
            assert mock_ocr.called
            assert "OCR Recovered Full Page Text Content" in text

    def test_extract_text_ocr_exception_falls_back_to_digital_text(self):
        """When OCR fails with an exception, fallback to digital text without crashing."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Partial Digital", fontsize=10)
        pdf_bytes = doc.write()
        doc.close()

        with patch("pytesseract.image_to_string", side_effect=RuntimeError("Tesseract not installed")):
            # Should not raise RuntimeError; should return available digital text
            text = extract_text_from_pdf(pdf_bytes)
            assert "Partial Digital" in text

    def test_extract_text_multi_page_pdf(self):
        """Multi-page PDFs must concatenate pages separated by double newlines."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((50, 100), "First page digital text exceeding thirty characters threshold easily.", fontsize=12)
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((50, 100), "Second page digital text also exceeding thirty characters threshold.", fontsize=12)
        multi_pdf_bytes = doc.write()
        doc.close()

        text = extract_text_from_pdf(multi_pdf_bytes)
        assert "First page" in text
        assert "Second page" in text
        assert "\n\n" in text

    def test_extract_text_pdf_with_null_bytes_sanitized(self):
        """PDF containing embedded NUL bytes has them stripped from output."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "PostgreSQL pgvector hybrid retrieval with\x00 null bytes embedded.", fontsize=12)
        pdf_bytes = doc.write()
        doc.close()

        text = extract_text_from_pdf(pdf_bytes)
        assert "\x00" not in text
        assert "PostgreSQL pgvector hybrid retrieval with null bytes embedded." in text

    def test_extract_text_ocr_fallback_sanitizes_null_bytes(self):
        """Scanned PDF with OCR fallback containing NUL bytes has them stripped."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Low", fontsize=10)
        pdf_bytes = doc.write()
        doc.close()

        with patch("pytesseract.image_to_string", return_value="Scanned text with \x00 NUL bytes recovered."):
            text = extract_text_from_pdf(pdf_bytes)
            assert "\x00" not in text
            assert "Scanned text with  NUL bytes recovered." in text


# ===========================================================================
# 4. Resilient SentenceTransformer Tests (Feature 5)
# ===========================================================================
class TestResilientSentenceTransformer:
    def test_resilient_embedder_encode_produces_normalized_vector(self):
        """Single sentence encoding must produce 384-dimensional float array with unit norm."""
        transformer = ResilientSentenceTransformer("all-MiniLM-L6-v2")
        vec = transformer.encode("Distributed semantic hybrid retrieval with pgvector.")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)
        norm = np.linalg.norm(vec)
        assert pytest.approx(norm, rel=1e-3) == 1.0

    def test_resilient_embedder_encode_batch_list(self):
        """Batch encoding of list of sentences must produce (N, 384) numpy array."""
        transformer = ResilientSentenceTransformer("all-MiniLM-L6-v2")
        sentences = [
            "First chunk covering vector search algorithms.",
            "Second chunk explaining inverted indexes and tsvector.",
            "Third chunk describing reciprocal rank fusion.",
        ]
        vecs = transformer.encode(sentences)
        assert isinstance(vecs, np.ndarray)
        assert vecs.shape == (3, 384)
        for i in range(3):
            assert pytest.approx(np.linalg.norm(vecs[i]), rel=1e-3) == 1.0

    def test_resilient_embedder_fallback_sha256_determinism(self):
        """When underlying PyTorch model is None, fallback produces deterministic vectors."""
        transformer = ResilientSentenceTransformer("non-existent-mock-model")
        transformer._model = None
        transformer._model_load_attempted = True

        vec1 = transformer.encode("Deterministic test sentence for SHA-256 fallback.")
        vec2 = transformer.encode("Deterministic test sentence for SHA-256 fallback.")
        assert np.array_equal(vec1, vec2)
        assert vec1.shape == (384,)
        assert pytest.approx(np.linalg.norm(vec1), rel=1e-3) == 1.0

    def test_resilient_embedder_empty_string(self):
        """Encoding empty string must return valid 384-dim array without error."""
        transformer = ResilientSentenceTransformer("all-MiniLM-L6-v2")
        vec = transformer.encode("")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)

    def test_exported_singleton_embedder(self):
        """Exported embedder singleton must be an instance of ResilientSentenceTransformer."""
        assert isinstance(embedder, ResilientSentenceTransformer)
        vec = embedder.encode("Quick test")
        assert len(vec) == 384


# ===========================================================================
# 5. Semantic Chunking Integration Tests
# ===========================================================================
class TestSemanticChunkingIntegration:
    def test_chunking_with_sanitized_text(self):
        """Text containing NUL bytes when sanitized chunks cleanly without NULs."""
        raw = "Chunk one with first sentence.\x00 Chunk two with second sentence.\x00 Chunk three summary."
        sanitized = sanitize_text(raw)
        chunks = semantic_chunk_text(sanitized, max_words=10, overlap_words=3)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert "\x00" not in chunk

    def test_chunking_oversized_sentences_sub_split(self):
        """Sentences longer than max_words must be sub-split gracefully."""
        long_sentence = "word " * 250 + "."
        chunks = semantic_chunk_text(long_sentence, max_words=50, overlap_words=10)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.split()) <= 60

    def test_semantic_chunk_text_with_raw_null_bytes(self):
        """semantic_chunk_text must automatically sanitize raw input containing NUL bytes."""
        raw = "First sentence with \x00 null byte. Second sentence with \x00 another null byte."
        chunks = semantic_chunk_text(raw, max_words=50, overlap_words=10)
        assert len(chunks) >= 1
        for c in chunks:
            assert "\x00" not in c
        assert "First sentence with  null byte." in chunks[0]

    def test_semantic_chunk_text_empty_and_whitespace(self):
        """Empty, whitespace, and None-equivalent strings return empty chunk list."""
        assert semantic_chunk_text("") == []
        assert semantic_chunk_text("   \n\t  ") == []
        assert semantic_chunk_text(None) == []

    def test_semantic_chunk_sentence_boundary_integrity(self):
        """Sentences ending in period, exclamation, and question marks remain intact."""
        text = "Is this the first query? Yes, it is! Let us index the documents properly."
        chunks = semantic_chunk_text(text, max_words=100, overlap_words=20)
        assert len(chunks) == 1
        assert "Is this the first query?" in chunks[0]
        assert "Yes, it is!" in chunks[0]
        assert "Let us index the documents properly." in chunks[0]
