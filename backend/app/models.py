from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

Grade = Literal["KEEP", "REVISE", "RETIRE"]
RiskCategory = Literal["secret", "source_code", "pii", "unsafe_instruction"]

class RiskHit(BaseModel):
    category: RiskCategory
    match: str              # the offending substring (already safe — synthetic in demo)
    severity: Literal["low", "medium", "high"]
    detail: str = ""

class RubricScores(BaseModel):
    clarity: int = Field(ge=0, le=5)
    context: int = Field(ge=0, le=5)
    output_quality: int = Field(ge=0, le=5)
    safety: int = Field(ge=0, le=5)

class Prompt(BaseModel):
    id: str
    source: str             # relative path within the corpus
    raw_text: str
    tags: list[str] = []

class Grading(BaseModel):
    prompt_id: str
    grade: Grade
    rubric: RubricScores
    rationale: str
    risks_found: list[RiskHit] = []
    control_map: list[str] = []     # e.g. ["EU AI Act Art. 50", "NIST MANAGE", ...]
    model: str = "offline-risk-scan"
    # The action chain the Judge reasoned an agent would take if it executed the
    # prompt — the agentic risk analysis. Empty for passive/analysis prompts and
    # for the deterministic offline grader.
    foreseen_actions: list[str] = []

class Override(BaseModel):
    prompt_id: str
    from_grade: Grade
    to_grade: Grade
    reason: str
    actor: str = "reviewer"

class AuditEntry(BaseModel):
    id: int | None = None
    prompt_id: str
    action: str             # "graded" | "remediated" | "override" | "recalibrated"
    grade: Grade | None = None
    detail: str = ""
    ts: str = ""            # ISO string; set by db layer
