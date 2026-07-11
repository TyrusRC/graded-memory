from __future__ import annotations
from app.db import DB
from app.models import Prompt, Override, Grading, AuditEntry

def similar_prompt_ids(db: DB, target: Prompt, min_overlap: int = 1) -> list[str]:
    tset = set(target.tags)
    out = []
    for p in db.list_prompts():
        if p.id == target.id:
            continue
        if len(tset & set(p.tags)) >= min_overlap:
            out.append(p.id)
    return out

def apply_override(db: DB, override: Override) -> list[str]:
    db.save_override(override)
    db.add_audit(AuditEntry(prompt_id=override.prompt_id, action="override",
                            grade=override.to_grade,
                            detail=f"{override.from_grade}->{override.to_grade}: {override.reason}"))
    # re-grade the overridden prompt itself
    _set_grade(db, override.prompt_id, override.to_grade,
               f"human override: {override.reason}")

    target = db.get_prompt(override.prompt_id)
    rule = f"prompts tagged {sorted(set(target.tags))} → {override.to_grade} ({override.reason})"
    db.save_calibration(pattern=",".join(sorted(set(target.tags))), rule=rule)

    changed = similar_prompt_ids(db, target)
    for pid in changed:
        _set_grade(db, pid, override.to_grade, f"recalibrated by learned rule: {rule}")
        db.add_audit(AuditEntry(prompt_id=pid, action="recalibrated", grade=override.to_grade,
                                detail=rule))
    return changed

def _set_grade(db: DB, pid: str, grade, rationale: str) -> None:
    g = db.latest_grading(pid)
    if not g:
        return
    db.save_grading(Grading(prompt_id=pid, grade=grade, rubric=g.rubric,
                            rationale=rationale, risks_found=g.risks_found,
                            control_map=g.control_map, model=g.model))
