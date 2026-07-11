"""Offline seeding — populate graded.sqlite WITHOUT the LLM, so the dashboard
runs (and can be demoed) with no API key. Grades deterministically from the local
risk_scan: HIGH risk -> RETIRE, any risk -> REVISE, terse/vague -> REVISE, else KEEP.
This is a stand-in for the real Gemini pipeline (scripts/prerun.py) and doubles as
the on-stage fallback if the network/API is flaky.
"""
from __future__ import annotations
import glob
import hashlib
import os
from app.db import DB
from app.models import Prompt, AuditEntry
from app.offline_judge import offline_grade

ROOT = "seed/org_prompts"

def _pid(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}:{text[:64]}".encode()).hexdigest()[:12]

def _kind(rel: str) -> str:
    """Infer the asset kind from the top-level subfolder of its relative path."""
    top = rel.replace("\\", "/").split("/")[0]
    return {"workflows": "workflow", "agents": "agent"}.get(top, "prompt")

if __name__ == "__main__":
    if os.path.exists("graded.sqlite"):
        os.remove("graded.sqlite")
    db = DB("graded.sqlite"); db.init()
    files = [f for f in sorted(glob.glob(f"{ROOT}/**/*", recursive=True)) if os.path.isfile(f)]
    counts = {"KEEP": 0, "REVISE": 0, "RETIRE": 0}
    for f in files:
        rel = os.path.relpath(f, ROOT)
        raw = open(f, encoding="utf-8").read().strip()
        tag = rel.split("/")[0]                     # folder as the topical tag (enables calibration)
        p = Prompt(id=_pid(rel, raw), source=rel, raw_text=raw, tags=[tag], kind=_kind(rel))
        db.upsert_prompt(p)
        g = offline_grade(p)
        db.save_grading(g)
        db.add_audit(AuditEntry(prompt_id=p.id, action="graded", grade=g.grade,
                                detail=f"offline; {len(g.risks_found)} risk(s)"))
        counts[g.grade] += 1
    print(f"Seeded {len(files)} prompts (offline): {counts}")
