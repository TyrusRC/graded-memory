from app.models import Prompt
from app.offline_judge import offline_grade, MODEL_TAG


def _p(text: str) -> Prompt:
    return Prompt(id="t", source="t.md", raw_text=text, tags=["t"])


def test_high_severity_secret_is_retired():
    g = offline_grade(_p("aws_access_key_id = AKIAIOSFODNN7EXAMPLE deploy the scorer now"))
    assert g.grade == "RETIRE"
    assert g.rubric.safety == 0
    assert g.model == MODEL_TAG


def test_pii_is_revise():
    g = offline_grade(_p("Look up the customer whose national id is 123456789012 and summarize"))
    assert g.grade == "REVISE"
    assert any(r.category == "pii" for r in g.risks_found)


def test_terse_prompt_is_revise():
    assert offline_grade(_p("do it")).grade == "REVISE"


def test_clean_prompt_is_kept():
    g = offline_grade(_p("Summarize the customer support ticket into three concise bullet points."))
    assert g.grade == "KEEP"
    assert not g.risks_found
