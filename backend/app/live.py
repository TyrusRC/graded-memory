"""Live-then-offline orchestration for the on-stage hero endpoints. Attempt the
real Gemini agent; if the free-tier quota is spent (or any API error), fall back
to the deterministic path so a demo never hard-fails on a 429. Keeps the HTTP
layer (main.py) thin and this fallback policy unit-testable without a network."""
from __future__ import annotations
from google.genai import errors as genai_errors
from app.models import Prompt, Grading
from app.judge import grade_prompt
from app.remediation import remediate
from app.offline_judge import offline_grade
from app.risk_scan import redact


def safe_grade(prompt: Prompt) -> Grading:
    try:
        return grade_prompt(prompt)
    except genai_errors.APIError:
        return offline_grade(prompt)   # quota/API down: deterministic grade keeps the demo alive


def safe_remediate(prompt: Prompt) -> tuple[Prompt, Grading]:
    try:
        return remediate(prompt)
    except genai_errors.APIError:
        # Deterministic remediation: redact() already masks secrets/PII/code to placeholders.
        fixed = Prompt(id=prompt.id, source=prompt.source, raw_text=redact(prompt.raw_text), tags=prompt.tags)
        return fixed, offline_grade(fixed)
