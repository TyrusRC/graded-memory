from __future__ import annotations
import time
from app.db import DB
from app.collector import collect
from app.judge import grade_prompt
from app.llm import MODEL
from app.models import AuditEntry

def run_pipeline(db: DB, root: str, client=None, pace: float = 4.0, resume: bool = True) -> None:
    prompts = collect(root, client=client)
    for i, p in enumerate(prompts):
        db.upsert_prompt(p)
        # Resume: skip prompts already graded by the real model so a rerun after a
        # 429 never re-spends the free-tier daily quota on completed work.
        prev = db.latest_grading(p.id)
        if resume and prev and prev.model == MODEL:
            print(f"  [{i+1}/{len(prompts)}] {p.source} -> {prev.grade} (cached, skip)")
            continue
        g = grade_prompt(p, client=client)   # with_retry inside handles 429s
        db.save_grading(g)
        db.add_audit(AuditEntry(prompt_id=p.id, action="graded", grade=g.grade,
                                detail=f"{len(g.risks_found)} risk(s)"))
        print(f"  [{i+1}/{len(prompts)}] {p.source} -> {g.grade}")
        time.sleep(pace)   # respect free-tier requests/minute; tune if you hit 429s
    print(f"Pipeline done: {len(prompts)} prompts graded.")
