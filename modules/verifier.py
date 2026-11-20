"""Stage 4 verifies each candidate clause against the original source text."""
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from modules.llm import generate_json, render_prompt
from modules.schemas import VERIFICATION


def verify_risks(text: str, candidates: list[dict]) -> dict:
    if not candidates:
        return {"verified_risks": [], "rejected_count": 0, "verification_notes": []}
    prompt = render_prompt("04_verify.txt", document=text, candidates=json.dumps(candidates, ensure_ascii=False))
    result = generate_json(prompt, VERIFICATION)
    # A second local guard requires a meaningful excerpt match, protecting against
    # a verifier response that accidentally invents or substantially rewrites text.
    source = " ".join(text.casefold().split())
    kept = []
    for risk in result["verified_risks"]:
        excerpt = " ".join(risk["original_excerpt"].casefold().split())
        if excerpt and (excerpt in source or _token_coverage(excerpt, source) >= 0.9):
            kept.append(risk)
    result["rejected_count"] += len(result["verified_risks"]) - len(kept)
    result["verified_risks"] = kept
    return result


def _token_coverage(excerpt: str, source: str) -> float:
    """Return the best ordered, local coverage of excerpt words in the source.

    The match may start after a missing leading word and may tolerate a small
    spelling/inflection difference. Source insertions are allowed, but candidate
    words must still align in order within a nearby source window.
    """
    tokens = re.findall(r"\w+", excerpt.casefold())
    source_tokens = re.findall(r"\w+", source.casefold())
    if not tokens or not source_tokens:
        return 0.0

    positions = defaultdict(list)
    for index, word in enumerate(source_tokens):
        positions[word].append(index)
    frequencies = Counter(source_tokens)

    # Anchor local comparisons on the rarest excerpt word that occurs verbatim.
    # This avoids scanning every possible window in a long source document and
    # still works when the excerpt's first word is absent from the source.
    anchors = [(frequencies[word], index, word) for index, word in enumerate(tokens) if frequencies[word]]
    if not anchors:
        return 0.0
    _, anchor_index, anchor_word = min(anchors)

    starts = set()
    for position in positions[anchor_word]:
        expected_start = position - anchor_index
        starts.update(range(max(0, expected_start - 2), min(len(source_tokens), expected_start + 3)))

    best = 0.0
    min_window = max(1, len(tokens) - 2)
    max_window = len(tokens) + 2
    for start in starts:
        for window_size in range(min_window, max_window + 1):
            window = source_tokens[start:start + window_size]
            if not window:
                continue
            best = max(best, _ordered_fuzzy_coverage(tokens, window))
            if best == 1.0:
                return best
    return best


def _ordered_fuzzy_coverage(excerpt_tokens: list[str], source_window: list[str]) -> float:
    """Weighted longest ordered match; unmatched source words do not penalize."""
    previous = [0.0] * (len(source_window) + 1)
    for excerpt_token in excerpt_tokens:
        current = [0.0]
        for index, source_token in enumerate(source_window, start=1):
            similarity = 1.0 if excerpt_token == source_token else SequenceMatcher(
                None, excerpt_token, source_token, autojunk=False
            ).ratio()
            match = previous[index - 1] + similarity if similarity >= 0.8 else 0.0
            current.append(max(previous[index], current[-1], match))
        previous = current
    return previous[-1] / len(excerpt_tokens)
