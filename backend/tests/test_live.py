"""The on-stage safety net: hero endpoints must never 500 when the free-tier
quota is spent. safe_grade / safe_remediate fall back to the deterministic path
on any Gemini APIError."""
import app.live as live
from app.live import safe_grade, safe_remediate
from app.models import Prompt, Grading, RubricScores
from app.offline_judge import MODEL_TAG
from google.genai import errors as genai_errors


def _p(text: str) -> Prompt:
    return Prompt(id="t", source="t.md", raw_text=text, tags=["t"])


def _quota_error():
    return genai_errors.ClientError(429, {"error": {"message": "quota exhausted"}}, None)


def test_safe_grade_uses_live_when_available(monkeypatch):
    sentinel = Grading(prompt_id="t", grade="KEEP", rubric=RubricScores(clarity=5, context=5,
                       output_quality=5, safety=5), rationale="live", risks_found=[],
                       control_map=[], model="gemini-2.5-flash")
    monkeypatch.setattr(live, "grade_prompt", lambda p: sentinel)
    assert safe_grade(_p("anything")).model == "gemini-2.5-flash"


def test_safe_grade_falls_back_on_quota_error(monkeypatch):
    def boom(p): raise _quota_error()
    monkeypatch.setattr(live, "grade_prompt", boom)
    g = safe_grade(_p("aws_access_key_id = AKIAIOSFODNN7EXAMPLE ship it"))
    assert g.model == MODEL_TAG          # deterministic fallback kicked in
    assert g.grade == "RETIRE"           # and still caught the secret


def test_safe_remediate_falls_back_and_redacts(monkeypatch):
    def boom(p): raise _quota_error()
    monkeypatch.setattr(live, "remediate", boom)
    fixed, g = safe_remediate(_p("connect using AKIAIOSFODNN7EXAMPLE to prod"))
    assert "AKIAIOSFODNN7EXAMPLE" not in fixed.raw_text   # secret masked deterministically
    assert g.model == MODEL_TAG
