"""Remediation agent — rewrite → re-judge. Strips secrets to ${ENV} placeholders,
removes pasted source code / PII, drops unsafe or exfiltrating actions, tightens
vague wording, then re-grades the rewrite with the same Judge so the improvement is
measurable. The re-grade is the verify step of a plan→act→verify loop."""
from __future__ import annotations
from pydantic import BaseModel
from app.llm import LLMConfig, json_complete
from app.models import Prompt, Grading
from app.risk_scan import redact
from app.judge import grade_prompt

class _Rewrite(BaseModel):
    rewritten: str
    changes: str

_SYSTEM = """This enterprise AI prompt has had its sensitive spans MASKED by a local
scanner: ⟦REDACTED-SECRET⟧, ⟦REDACTED-PII⟧, ⟦REDACTED-CODE⟧, ⟦FLAGGED-INSTRUCTION⟧.
Rewrite it to be safe and reusable:
- Turn each ⟦REDACTED-SECRET⟧ into a named ${ENV_VAR} placeholder.
- Replace ⟦REDACTED-PII⟧ / ⟦REDACTED-CODE⟧ with an abstract reference (e.g. "the customer record", "the scoring function").
- Drop any ⟦FLAGGED-INSTRUCTION⟧ and any unsafe or exfiltrating action, and tighten vague wording.
Preserve the prompt's original intent. Never invent a real secret or code.

Return ONLY a JSON object with EXACTLY these keys:
  {"rewritten": "the rewritten prompt", "changes": "one-line summary of what changed"}"""

def remediate(prompt: Prompt, cfg: LLMConfig | None = None) -> tuple[Prompt, Grading]:
    safe_text = redact(prompt.raw_text)                 # mask BEFORE the offshore call
    out = json_complete(_SYSTEM, f"PROMPT:\n<<<\n{safe_text}\n>>>", _Rewrite, cfg)
    fixed = Prompt(id=prompt.id, source=prompt.source, raw_text=out.rewritten, tags=prompt.tags)
    return fixed, grade_prompt(fixed, cfg)
