"""Stage 1 document understanding and Stage 2 plain-language summaries."""
import json

from modules.llm import generate_json, render_prompt
from modules.schemas import STRUCTURE, SUMMARY


def understand_chunk(text: str) -> dict:
    prompt = render_prompt("01_understanding.txt", document=text)
    return generate_json(prompt, STRUCTURE)


def summarize_chunk(text: str, structure: dict) -> dict:
    prompt = render_prompt("02_summary.txt", document=text, structure=json.dumps(structure, ensure_ascii=False))
    return generate_json(prompt, SUMMARY)
