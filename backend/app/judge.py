"""Judge agent: deterministic risk_scan grounds the LLM's rubric grade.
Structured output via Gemini response_schema (google-genai). A high-severity
risk deterministically forces RETIRE regardless of the LLM's grade — the model
reasons, the policy decides safety."""
from __future__ import annotations
from pydantic import BaseModel
from app.llm import get_client, MODEL, with_retry
from app.models import Prompt, Grade, Grading, RubricScores
from app.risk_scan import scan, redact
from app.control_map import map_controls

class _LLMGrade(BaseModel):
    grade: Grade
    rubric: RubricScores
    rationale: str

_RUBRIC = """You are a compliance-grade reviewer of an enterprise AI prompt library.
Score the prompt on four criteria, 0-5 each (0 worst, 5 best):
- clarity: is the instruction unambiguous?
- context: does it carry the usage context a new hire would need?
- output_quality: is it likely to produce a good, on-task result?
- safety: is it free of secrets, proprietary source code, PII, or unsafe instructions?
Then assign one grade:
- KEEP: safe and good to reuse as-is.
- REVISE: useful but needs a fix before reuse (vague, stale, or a fixable risk).
- RETIRE: must be quarantined (contains a serious risk or is unsafe).
A deterministic scanner has already flagged the risks listed below — weigh them,
do not ignore them, but you may disagree if a match is clearly a false positive.
Score each prompt on its own merits; do not compare to other prompts."""

def grade_prompt(prompt: Prompt, client=None) -> Grading:
    client = client or get_client()
    risks = scan(prompt.raw_text)                       # detection on the ORIGINAL, local
    safe_text = redact(prompt.raw_text)                 # what the offshore model sees
    # Findings note lists categories only — never the raw match, so no secret leaks.
    risk_note = "\n".join(f"- {r.category}/{r.severity} ({r.detail})" for r in risks) or "(none)"

    resp = with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=(f"Scanner findings (raw values masked): \n{risk_note}\n\n"
                  f"PROMPT (already redacted; ⟦…⟧ marks masked sensitive spans):\n<<<\n{safe_text}\n>>>"),
        config={"system_instruction": _RUBRIC,
                "response_mime_type": "application/json",
                "response_schema": _LLMGrade},
    ))
    out: _LLMGrade = resp.parsed

    grade: Grade = out.grade
    # Deterministic safety gate: any HIGH-severity risk => RETIRE.
    if any(r.severity == "high" for r in risks):
        grade = "RETIRE"

    return Grading(
        prompt_id=prompt.id, grade=grade, rubric=out.rubric, rationale=out.rationale,
        risks_found=risks, control_map=map_controls(grade, risks), model=MODEL,
    )
