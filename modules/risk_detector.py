"""Stage 3 identification of potentially concerning, text-supported clauses."""
import json

from modules.llm import generate_json, render_prompt
from modules.schemas import CANDIDATES


def detect_risks(text: str) -> list[dict]:
    result = generate_json(render_prompt("03_risks.txt", document=text), CANDIDATES)
    return result["risks"]
