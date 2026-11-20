# ClauseWise architecture

The app follows five prompt stages, with each template kept in `prompts/`:

1. `summarizer.understand_chunk` extracts title, document type, and section descriptions.
2. `summarizer.summarize_chunk` explains each chunk and extracts rights and obligations.
3. `risk_detector.detect_risks` looks for the eight monitored risk categories.
4. `verifier.verify_risks` checks excerpts and explanations against the original source, then applies a local excerpt-support guard.
5. `pipeline.analyze_document` assembles the results into the strict frontend JSON schema.

`document_processor` enforces the extracted-text character limit and creates overlapping chunks. `pdf_extractor` validates PDFs, rejects encrypted or empty/scanned documents, and labels extracted pages. `llm` owns Gemini calls, prompt loading, and JSON Schema validation. The Streamlit `app.py` handles input, progress, display, and JSON download.

The output is educational and informational. A “risk” is a prompt-based review signal, not a conclusion that a clause is unlawful or enforceable.
