"""Live-then-offline orchestration for the on-stage hero endpoints. Attempt the real
LLM agent; if the provider errors (rate limit, bad response, outage) fall back to the
deterministic grader so a demo never hard-fails. Runs deterministically by default when
no provider key is configured, so a public deploy needs no key. Keeps the HTTP layer
(main.py) thin and this fallback policy unit-testable without a network."""
from __future__ import annotations
import os
from app.llm import LLMConfig, LLMError, has_llm
from app.models import Prompt, Grading
from app.judge import grade_prompt
from app.remediation import remediate
from app.offline_judge import offline_grade
from app.risk_scan import redact


def _is_offline(cfg: LLMConfig | None = None) -> bool:
    # Deterministic when explicitly forced OR when no provider (per-request or env) is configured.
    return os.environ.get("GM_OFFLINE") == "1" or not has_llm(cfg)


def _offline_remediate(prompt: Prompt) -> tuple[Prompt, Grading]:
    # redact() already masks secrets/PII/code to placeholders before re-grading.
    fixed = Prompt(id=prompt.id, source=prompt.source, raw_text=redact(prompt.raw_text), tags=prompt.tags)
    return fixed, offline_grade(fixed)


def _annotate_fallback(g: Grading, exc: Exception) -> Grading:
    # A key IS configured but the live call failed: say so in the model tag instead of
    # silently showing an offline grade, so BYOK misconfig is diagnosable, not a mystery.
    g.model = f"{g.model} (live LLM failed: {type(exc).__name__})"
    return g


def safe_grade(prompt: Prompt, cfg: LLMConfig | None = None) -> Grading:
    if _is_offline(cfg):
        return offline_grade(prompt)
    try:
        return grade_prompt(prompt, cfg)
    except LLMError as e:
        return _annotate_fallback(offline_grade(prompt), e)   # provider down/quota/bad response: deterministic grade keeps the demo alive


def safe_remediate(prompt: Prompt, cfg: LLMConfig | None = None) -> tuple[Prompt, Grading]:
    if _is_offline(cfg):
        return _offline_remediate(prompt)
    try:
        return remediate(prompt, cfg)
    except LLMError as e:
        fixed, g = _offline_remediate(prompt)
        return fixed, _annotate_fallback(g, e)
