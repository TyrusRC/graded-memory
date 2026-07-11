"""Deterministic reuse surface (NO LLM) — P5 "surface relevant prior work when an
employee starts a new task." Similarity is Jaccard over lowercased word tokens minus
a small English stopword set, so a new task's wording maps to graded prior art."""
from __future__ import annotations
import re
from app.models import Prompt, Grading

_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "this",
    "that", "these", "those", "it", "its", "into", "then", "than", "so", "if",
    "your", "you", "our", "we", "i", "me", "my", "them", "they", "he", "she",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"\w+", text.lower()) if t not in _STOP}


def similarity(a: str, b: str) -> float:
    """Jaccard overlap of content-word tokens; 0..1."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def find_similar(query_text: str, prompts: list[Prompt], gradings: dict[str, Grading],
                 *, top_n: int = 3, only_grade: str | None = "KEEP",
                 kind: str | None = None) -> list[dict]:
    """Rank prior artifacts by similarity to query_text. Excludes the query itself
    (identical raw_text), filters to gradings[pid].grade == only_grade when set, and
    to prompt.kind == kind when set. Returns [{"prompt_id", "score"}] score>0 desc."""
    scored: list[dict] = []
    for p in prompts:
        if p.raw_text == query_text:
            continue
        if kind is not None and p.kind != kind:
            continue
        if only_grade is not None:
            g = gradings.get(p.id)
            if not g or g.grade != only_grade:
                continue
        score = similarity(query_text, p.raw_text)
        if score > 0:
            scored.append({"prompt_id": p.id, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
