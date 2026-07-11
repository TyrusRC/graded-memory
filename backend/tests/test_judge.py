from unittest.mock import MagicMock
from app.judge import grade_prompt
from app.models import Prompt, RubricScores

def _mock_client(grade, rubric, rationale):
    from app.judge import _LLMGrade
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(
        parsed=_LLMGrade(grade=grade, rubric=rubric, rationale=rationale))
    return client

def test_high_severity_secret_forces_retire_even_if_llm_says_keep():
    p = Prompt(id="p1", source="a.md",
               raw_text="deploy with AKIAIOSFODNN7EXAMPLE key")
    rubric = RubricScores(clarity=4, context=4, output_quality=4, safety=4)
    client = _mock_client("KEEP", rubric, "looks fine")  # LLM wrong on purpose
    g = grade_prompt(p, client=client)
    assert g.grade == "RETIRE"                    # deterministic override
    assert any(r.category == "secret" for r in g.risks_found)
    assert g.control_map                          # controls mapped

def test_clean_prompt_takes_llm_grade():
    p = Prompt(id="p2", source="b.md", raw_text="Summarize this ticket in 2 sentences.")
    rubric = RubricScores(clarity=5, context=4, output_quality=5, safety=5)
    client = _mock_client("KEEP", rubric, "clear and safe")
    g = grade_prompt(p, client=client)
    assert g.grade == "KEEP" and g.risks_found == []
