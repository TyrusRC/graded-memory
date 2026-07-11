from __future__ import annotations
import csv, io, hashlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.db import DB
from app.models import Prompt, Override, AuditEntry
from app.live import safe_grade, safe_remediate
from app.calibration import apply_override

db = DB()
db.init()
app = FastAPI(title="Graded Memory")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def _row(pid: str) -> dict:
    p, g = db.get_prompt(pid), db.latest_grading(pid)
    return {"prompt": p.model_dump(), "grading": g.model_dump() if g else None}

@app.get("/api/library")
def library():
    return [_row(p.id) for p in db.list_prompts()]

@app.get("/api/newhire")
def newhire():
    return [_row(p.id) for p in db.list_prompts() if (g := db.latest_grading(p.id)) and g.grade == "KEEP"]

@app.get("/api/prompt/{pid}")
def prompt_detail(pid: str):
    if not db.get_prompt(pid):
        raise HTTPException(404)
    audit = [a.model_dump() for a in db.list_audit() if a.prompt_id == pid]
    return {**_row(pid), "audit": audit}

@app.get("/api/audit")
def audit():
    return [a.model_dump() for a in db.list_audit()]

@app.get("/api/audit/export.csv")
def audit_csv():
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["ts", "prompt_id", "action", "grade", "detail"])
    for a in db.list_audit():
        w.writerow([a.ts, a.prompt_id, a.action, a.grade, a.detail])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=graded-memory-audit.csv"})

@app.get("/api/calibration")
def calibration():
    return db.list_calibration()

class GradeReq(BaseModel):
    text: str

@app.post("/api/grade")
def live_grade(req: GradeReq):
    pid = "live-" + hashlib.sha1(req.text.encode()).hexdigest()[:8]
    p = Prompt(id=pid, source="live-demo", raw_text=req.text, tags=["live"])
    db.upsert_prompt(p)
    g = safe_grade(p)
    db.save_grading(g)
    db.add_audit(AuditEntry(prompt_id=pid, action="graded", grade=g.grade,
                            detail=f"live; {len(g.risks_found)} risk(s)"))
    return _row(pid)

@app.post("/api/remediate/{pid}")
def live_remediate(pid: str):
    p = db.get_prompt(pid)
    if not p:
        raise HTTPException(404)
    fixed, g = safe_remediate(p)
    db.upsert_prompt(fixed); db.save_grading(g)
    db.add_audit(AuditEntry(prompt_id=pid, action="remediated", grade=g.grade, detail="rewrite+re-judge"))
    return _row(pid)

class OverrideReq(BaseModel):
    prompt_id: str
    to_grade: str
    reason: str

@app.post("/api/override")
def override(req: OverrideReq):
    cur = db.latest_grading(req.prompt_id)
    if not cur:
        raise HTTPException(404)
    changed = apply_override(db, Override(prompt_id=req.prompt_id, from_grade=cur.grade,
                                          to_grade=req.to_grade, reason=req.reason))
    return {"changed": changed, "count": len(changed)}
