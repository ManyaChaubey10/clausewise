import pytest

from modules.document_processor import chunk_document, validate_document
from modules.pdf_extractor import DocumentInputError


def test_validate_document_rejects_empty_input():
    with pytest.raises(DocumentInputError):
        validate_document("  ")


def test_validate_document_trims_text():
    assert validate_document("  terms  ") == "terms"


def test_chunk_document_covers_all_source_text_with_overlap():
    text = "A" * 80
    chunks = chunk_document(text, chunk_chars=30, overlap=5)
    assert len(chunks) > 1
    assert "".join(chunks).startswith(text[:30])
    assert all(len(chunk) <= 30 for chunk in chunks)


def test_chunk_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_document("text", chunk_chars=10, overlap=10)
