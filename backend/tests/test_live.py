"""The on-stage safety net: hero endpoints must never 500 when the provider errors.
safe_grade / safe_remediate fall back to the deterministic path on any LLM error, and
run deterministically by default when no key is configured."""
import app.live as live
from app.live import safe_grade, safe_remediate
from app.models import Prompt, Grading, RubricScores
from app.offline_judge import MODEL_TAG
from openai import APIError


def _p(text: str) -> Prompt:
    return Prompt(id="t", source="t.md", raw_text=text, tags=["t"])


def _force_live(monkeypatch):
    # No key is configured in the test env, so the app is offline by default; pretend a
    # provider is present so the live path (and its fallback) is exercised.
    monkeypatch.setattr(live, "_is_offline", lambda cfg=None: False)


def _quota_error():
    return APIError("quota exhausted", request=None, body=None)


def test_no_key_defaults_to_offline():
    # With no provider configured the app grades deterministically, no monkeypatching.
    g = safe_grade(_p("Summarize this ticket in two sentences."))
    assert g.model == MODEL_TAG


def test_safe_grade_uses_live_when_available(monkeypatch):
    _force_live(monkeypatch)
    sentinel = Grading(prompt_id="t", grade="KEEP", rubric=RubricScores(clarity=5, context=5,
                       output_quality=5, safety=5), rationale="live", risks_found=[],
                       control_map=[], model="qwen-plus")
    monkeypatch.setattr(live, "grade_prompt", lambda p, cfg=None: sentinel)
    assert safe_grade(_p("anything")).model == "qwen-plus"


def test_safe_grade_falls_back_on_provider_error(monkeypatch):
    _force_live(monkeypatch)
    def boom(p, cfg=None): raise _quota_error()
    monkeypatch.setattr(live, "grade_prompt", boom)
    g = safe_grade(_p("aws_access_key_id = AKIAIOSFODNN7EXAMPLE ship it"))
    assert g.model.startswith(MODEL_TAG)  # deterministic fallback kicked in
    assert "live LLM failed" in g.model   # and the failure is surfaced, not hidden
    assert g.grade == "RETIRE"           # and still caught the secret


def test_safe_remediate_falls_back_and_redacts(monkeypatch):
    _force_live(monkeypatch)
    def boom(p, cfg=None): raise _quota_error()
    monkeypatch.setattr(live, "remediate", boom)
    fixed, g = safe_remediate(_p("connect using AKIAIOSFODNN7EXAMPLE to prod"))
    assert "AKIAIOSFODNN7EXAMPLE" not in fixed.raw_text   # secret masked deterministically
    assert g.model.startswith(MODEL_TAG)
