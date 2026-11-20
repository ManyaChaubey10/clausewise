"""Runs the five ClauseWise prompt stages over a chunked document."""
import json

from modules.document_processor import chunk_document, validate_document
from modules.llm import generate_json, render_prompt
from modules.risk_detector import detect_risks
from modules.schemas import FINAL
from modules.summarizer import summarize_chunk, understand_chunk
from modules.verifier import verify_risks


def analyze_document(text: str, progress=None) -> dict:
    text = validate_document(text)
    chunks = chunk_document(text)
    structures, summaries, candidates = [], [], []
    total = len(chunks) * 3 + 2
    done = 0
    def tick(label):
        nonlocal done
        done += 1
        if progress:
            progress(done / total, label)

    for index, chunk in enumerate(chunks, start=1):
        structure = understand_chunk(chunk)
        structures.append(structure)
        tick(f"Understanding document section {index} of {len(chunks)}")
        summaries.append(summarize_chunk(chunk, structure))
        tick(f"Summarising section {index} of {len(chunks)}")
        candidates.extend(detect_risks(chunk))
        tick(f"Checking potential risks in section {index} of {len(chunks)}")
    # Verify against the original, unchunked source so overlap cannot hide context.
    verification = verify_risks(text, candidates)
    tick("Verifying each flagged clause against the source")
    stage1 = {
        "title": next((x["title"] for x in structures if x["title"]), "Untitled document"),
        "document_type": next((x["document_type"] for x in structures if x["document_type"]), "Terms and conditions or privacy policy"),
        "sections": [section for item in structures for section in item["sections"]],
    }
    stage2 = {
        "summary": "\n\n".join(item["summary"] for item in summaries),
        "important_obligations": _dedupe(v for item in summaries for v in item["important_obligations"]),
        "user_rights": _dedupe(v for item in summaries for v in item["user_rights"]),
        "unclear_points": _dedupe(v for item in summaries for v in item["unclear_points"]),
    }
    final_prompt = render_prompt("05_output.txt",
        structure=json.dumps(stage1, ensure_ascii=False),
        summary=json.dumps(stage2, ensure_ascii=False),
        verified=json.dumps(verification, ensure_ascii=False),
    )
    result = generate_json(final_prompt, FINAL)
    tick("Preparing the structured report")
    # Ensure frontend risks are the precisely verified set from Stage 4.
    result["risks"] = verification["verified_risks"]
    return result


def _dedupe(items):
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))
