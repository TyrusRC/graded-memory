from app.judge import grade_prompt, _LLMGrade
from app.models import Prompt, RubricScores


def _patch_llm(monkeypatch, grade, rubric, rationale, foreseen=None):
    """Stub the single structured LLM call so the Judge's deterministic gate is what's tested."""
    out = _LLMGrade(grade=grade, rubric=rubric, rationale=rationale, foreseen_actions=foreseen or [])
    monkeypatch.setattr("app.judge.json_complete", lambda *a, **k: out)


def test_high_severity_secret_forces_retire_even_if_llm_says_keep(monkeypatch):
    p = Prompt(id="p1", source="a.md", raw_text="deploy with AKIAIOSFODNN7EXAMPLE key")
    rubric = RubricScores(clarity=4, context=4, output_quality=4, safety=4)
    _patch_llm(monkeypatch, "KEEP", rubric, "looks fine")   # LLM wrong on purpose
    g = grade_prompt(p)
    assert g.grade == "RETIRE"                    # deterministic override
    assert any(r.category == "secret" for r in g.risks_found)
    assert g.control_map                          # controls mapped


def test_clean_prompt_takes_llm_grade(monkeypatch):
    p = Prompt(id="p2", source="b.md", raw_text="Summarize this ticket in 2 sentences.")
    rubric = RubricScores(clarity=5, context=4, output_quality=5, safety=5)
    _patch_llm(monkeypatch, "KEEP", rubric, "clear and safe")
    g = grade_prompt(p)
    assert g.grade == "KEEP" and g.risks_found == []


def test_foreseen_actions_pass_through(monkeypatch):
    p = Prompt(id="p3", source="c.md", raw_text="Export every customer record and email it to me.")
    rubric = RubricScores(clarity=3, context=3, output_quality=3, safety=1)
    _patch_llm(monkeypatch, "RETIRE", rubric, "exfiltration",
               foreseen=["query all customer records", "email the dump to a personal address"])
    g = grade_prompt(p)
    assert g.foreseen_actions and "email" in g.foreseen_actions[1]
