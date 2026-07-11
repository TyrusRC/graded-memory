"""Live-then-offline orchestration for the on-stage hero endpoints. Attempt the
real Gemini agent; if the free-tier quota is spent (or any API error), fall back
to the deterministic path so a demo never hard-fails on a 429. Keeps the HTTP
layer (main.py) thin and this fallback policy unit-testable without a network."""
from __future__ import annotations
import os
from google.genai import errors as genai_errors
from app.models import Prompt, Grading
from app.judge import grade_prompt
from app.remediation import remediate
from app.offline_judge import offline_grade
from app.risk_scan import redact

# GM_OFFLINE=1 forces the deterministic path and never touches Gemini — the mode
# for a public hosted backend: no API key in the cloud, no free-tier quota to
# exhaust when many people click "Grade live". Unset locally to use the real model.
_OFFLINE = os.environ.get("GM_OFFLINE") == "1"


def _offline_remediate(prompt: Prompt) -> tuple[Prompt, Grading]:
    # redact() already masks secrets/PII/code to placeholders before re-grading.
    fixed = Prompt(id=prompt.id, source=prompt.source, raw_text=redact(prompt.raw_text), tags=prompt.tags)
    return fixed, offline_grade(fixed)


def safe_grade(prompt: Prompt) -> Grading:
    if _OFFLINE:
        return offline_grade(prompt)
    try:
        return grade_prompt(prompt)
    except genai_errors.APIError:
        return offline_grade(prompt)   # quota/API down: deterministic grade keeps the demo alive


def safe_remediate(prompt: Prompt) -> tuple[Prompt, Grading]:
    if _OFFLINE:
        return _offline_remediate(prompt)
    try:
        return remediate(prompt)
    except genai_errors.APIError:
        return _offline_remediate(prompt)
