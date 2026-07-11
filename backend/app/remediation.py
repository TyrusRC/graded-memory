"""Remediation agent — critique → rewrite → re-judge (spec 3b). Strips secrets
to ${ENV} placeholders, removes pasted source code / PII, tightens vague wording,
then re-grades the rewrite with the same Judge so the improvement is measurable."""
from __future__ import annotations
from pydantic import BaseModel
from app.llm import get_client, MODEL, with_retry
from app.models import Prompt, Grading
from app.risk_scan import redact
from app.judge import grade_prompt

class _Rewrite(BaseModel):
    rewritten: str
    changes: str

_INSTR = """This enterprise AI prompt has already had its sensitive spans MASKED
by a local scanner: ⟦REDACTED-SECRET⟧, ⟦REDACTED-PII⟧, ⟦REDACTED-CODE⟧,
⟦FLAGGED-INSTRUCTION⟧. Rewrite it to be safe and reusable:
- Turn each ⟦REDACTED-SECRET⟧ into a named ${ENV_VAR} placeholder.
- Replace ⟦REDACTED-PII⟧ / ⟦REDACTED-CODE⟧ with an abstract reference (e.g. "the customer record", "the scoring function").
- Drop any ⟦FLAGGED-INSTRUCTION⟧ and tighten vague wording.
Preserve the prompt's original intent. Never invent a real secret or code.
Return the rewritten prompt and a one-line summary of what you changed."""

def remediate(prompt: Prompt, client=None) -> tuple[Prompt, Grading]:
    client = client or get_client()
    safe_text = redact(prompt.raw_text)                 # mask BEFORE the offshore call
    resp = with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=f"{_INSTR}\n\nPROMPT:\n<<<\n{safe_text}\n>>>",
        config={"response_mime_type": "application/json", "response_schema": _Rewrite},
    ))
    fixed = Prompt(id=prompt.id, source=prompt.source,
                   raw_text=resp.parsed.rewritten, tags=prompt.tags)
    new_grading = grade_prompt(fixed, client=client)
    return fixed, new_grading
