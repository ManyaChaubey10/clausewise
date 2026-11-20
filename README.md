# ClauseWise

ClauseWise is an academic mini-project that turns Terms & Conditions and Privacy Policies into a plain-language summary, highlights user obligations and rights, and flags clauses that may deserve closer review.

## Project structure

- `app.py` — responsive Streamlit dashboard, document input, report display, JSON download.
- `config.py` — model selection, prompt location, chunk and upload limits.
- `modules/pdf_extractor.py` — PDF text extraction with page markers and input validation.
- `modules/document_processor.py` — empty/oversize validation and overlapping text chunks.
- `modules/summarizer.py` — Stage 1 document structure and Stage 2 plain-language summary.
- `modules/risk_detector.py` — Stage 3 identification of supported potential risks.
- `modules/verifier.py` — Stage 4 evidence verification and local excerpt matching guard.
- `modules/pipeline.py` — orchestration and Stage 5 final structured result.
- `modules/llm.py`, `modules/schemas.py` — Gemini client calls and strict JSON Schema validation.
- `prompts/` — independently editable templates for all five stages.
- `tests/` — basic tests for chunking, input validation, and excerpt support.
- `docs/architecture.md` — prompt-chain architecture notes.

## Setup

Use Python 3.10 or newer. From the `clausewise` directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env` to your Google AI Studio API key. Optionally set `GEMINI_MODEL`; the default is `gemini-2.5-flash`.

## Run

```powershell
streamlit run app.py
```

## Tests

```powershell
pytest
```

## Limits and accuracy notes

- PDF uploads are limited to 20 MB; extracted text is limited to 250,000 characters and is chunked with overlap.
- PDFs need selectable text. Image-only scans require OCR and currently receive a clear error.
- Each analysis stage uses Gemini and requires internet access and a valid API key. A long document may use multiple model requests.
- The model can miss nuance or make mistakes. The verifier checks candidates against the supplied source and rejects unsupported excerpts, but this does not guarantee legal or factual completeness.
- Risk levels are informational and are not legal judgments. The app does not automatically determine whether a clause is illegal.
