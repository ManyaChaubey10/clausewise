"""Normalize and split long documents into overlapping source-preserving chunks."""
from config import CHUNK_CHARS, CHUNK_OVERLAP, MAX_DOCUMENT_CHARS
from modules.pdf_extractor import DocumentInputError


def validate_document(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise DocumentInputError("Add document text or upload a PDF before analysing.")
    if len(cleaned) > MAX_DOCUMENT_CHARS:
        raise DocumentInputError(f"The extracted document is too large ({len(cleaned):,} characters). Limit: {MAX_DOCUMENT_CHARS:,} characters.")
    return cleaned


def chunk_document(text: str, chunk_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if chunk_chars <= overlap or overlap < 0:
        raise ValueError("chunk_chars must be greater than a non-negative overlap")
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + chunk_chars // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [part for part in chunks if part]
