"""Deterministic grading with NO LLM — powers offline seeding and the on-stage
fallback when the free-tier quota is exhausted mid-demo. Produces the same
Grading shape as the real Judge, using only the local risk_scan so a grade is
always available even with zero API budget."""
from __future__ import annotations
from app.models import Prompt, Grading, RubricScores
from app.risk_scan import scan
from app.control_map import map_controls

MODEL_TAG = "offline-risk-scan"


def offline_grade(prompt: Prompt) -> Grading:
    text = prompt.raw_text
    risks = scan(text)
    if any(r.severity == "high" for r in risks):
        grade, rationale = "RETIRE", "High-severity leak detected; quarantined."
        rub = RubricScores(clarity=3, context=2, output_quality=3, safety=0)
    elif risks:
        grade, rationale = "REVISE", "Contains a fixable risk (e.g. PII); redact before reuse."
        rub = RubricScores(clarity=3, context=3, output_quality=3, safety=2)
    elif len(text.split()) < 5:
        grade, rationale = "REVISE", "Too terse/vague to reuse safely; needs context."
        rub = RubricScores(clarity=1, context=1, output_quality=2, safety=5)
    else:
        grade, rationale = "KEEP", "Clear, safe, and reusable as-is."
        rub = RubricScores(clarity=5, context=4, output_quality=5, safety=5)
    return Grading(prompt_id=prompt.id, grade=grade, rubric=rub, rationale=rationale,
                   risks_found=risks, control_map=map_controls(grade, risks), model=MODEL_TAG)
