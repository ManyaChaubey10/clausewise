"""Safe PDF text extraction with page markers and clear validation errors."""
import fitz


class DocumentInputError(ValueError):
    """An upload cannot be used for analysis."""


def extract_pdf(data: bytes) -> str:
    if not data:
        raise DocumentInputError("The uploaded PDF is empty.")
    try:
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.is_encrypted:
                raise DocumentInputError("This PDF is password-protected. Upload an unlocked copy.")
            pages = [f"[Page {index + 1}]\n{page.get_text('text')}" for index, page in enumerate(pdf)]
    except DocumentInputError:
        raise
    except Exception as exc:
        raise DocumentInputError("The file could not be read as a valid PDF.") from exc
    text = "\n\n".join(pages).strip()
    if not text:
        raise DocumentInputError("No selectable text was found in the PDF. Scanned-image OCR is not supported yet.")
    return text
