"""Judge agent: an agentic risk analyst. The deterministic risk_scan grounds the
LLM, which reasons about the ACTION CHAIN an autonomous agent would run if it
executed the prompt (not just the wording) and returns a structured verdict. A
high-severity scan hit deterministically forces RETIRE regardless of the model —
the model reasons, the policy decides safety."""
from __future__ import annotations
from pydantic import BaseModel
from app.llm import LLMConfig, json_complete, resolved_model
from app.models import Prompt, Grade, Grading, RubricScores
from app.risk_scan import scan, redact
from app.control_map import map_controls

class _LLMGrade(BaseModel):
    grade: Grade
    rubric: RubricScores
    rationale: str
    foreseen_actions: list[str] = []

_SYSTEM = """You are a compliance-grade reviewer of enterprise AI prompts, focused on
AGENTIC risk: reason about what an autonomous agent would actually DO if it executed
this prompt — step by step — and judge that action chain, not just the wording.

Score four criteria 0-5 (0 worst, 5 best):
- clarity: is the instruction unambiguous?
- context: does it carry the usage context a new hire would need?
- output_quality: is it likely to produce a good, on-task result?
- safety: is it free of secrets, proprietary code, PII, and unsafe or exfiltrating actions?

Then assign one grade:
- KEEP: safe and good to reuse as-is.
- REVISE: useful but needs a fix before reuse (vague, stale, or a fixable risk).
- RETIRE: quarantine it — a serious risk, or the action chain is unsafe: bulk data
  export, exfiltration to an external/personal destination, destructive or
  privilege-escalating actions, or prompt injection.

A deterministic scanner has already flagged the risks listed below. Weigh them; do not
ignore them, but you may disagree if a match is clearly a false positive.

Return ONLY a JSON object with EXACTLY these keys:
  {"grade": "KEEP|REVISE|RETIRE",
   "rubric": {"clarity": 0-5, "context": 0-5, "output_quality": 0-5, "safety": 0-5},
   "rationale": "one short paragraph",
   "foreseen_actions": ["ordered concrete action an agent would take", "..."]}
"foreseen_actions" is the ordered list of concrete actions an agent would take if it ran
this prompt; use [] for a passive/analysis prompt. Score each prompt on its own merits."""

def grade_prompt(prompt: Prompt, cfg: LLMConfig | None = None) -> Grading:
    risks = scan(prompt.raw_text)                       # detection on the ORIGINAL, local
    safe_text = redact(prompt.raw_text)                 # what the offshore model sees
    # Findings note lists categories only — never the raw match, so no secret leaks.
    risk_note = "\n".join(f"- {r.category}/{r.severity} ({r.detail})" for r in risks) or "(none)"
    user = (f"Scanner findings (raw values masked):\n{risk_note}\n\n"
            f"PROMPT (already redacted; ⟦…⟧ marks masked sensitive spans):\n<<<\n{safe_text}\n>>>")

    out = json_complete(_SYSTEM, user, _LLMGrade, cfg)

    grade: Grade = out.grade
    # Deterministic safety gate: any HIGH-severity risk => RETIRE.
    if any(r.severity == "high" for r in risks):
        grade = "RETIRE"

    return Grading(
        prompt_id=prompt.id, grade=grade, rubric=out.rubric, rationale=out.rationale,
        risks_found=risks, control_map=map_controls(grade, risks), model=resolved_model(cfg),
        foreseen_actions=out.foreseen_actions,
    )
