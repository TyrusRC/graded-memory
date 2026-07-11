from __future__ import annotations
import csv, io, hashlib
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.db import DB
from app.models import Prompt, Override, AuditEntry
from app.live import safe_grade, safe_remediate
from app.llm import LLMConfig, LLMError, has_llm, ping
from app.calibration import apply_override
from app import reuse, analytics, webhooks

db = DB()
db.init()
app = FastAPI(title="Graded Memory")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def llm_cfg(
    x_llm_base_url: str | None = Header(default=None),
    x_llm_api_key: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
) -> LLMConfig:
    """Per-request bring-your-own-key config from browser headers. Never stored or logged;
    used only for this call. Empty header => that field falls back to the operator env default."""
    return LLMConfig(base_url=x_llm_base_url or None, api_key=x_llm_api_key or None,
                     model=x_llm_model or None)

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
    kind: str = "prompt"
    context: str = ""

@app.get("/api/llm/status")
def llm_status(cfg: LLMConfig = Depends(llm_cfg)):
    """Powers the green dot. Offline (grey) when no provider is configured; probes the
    configured provider with a tiny call and reports online (green) / error (red)."""
    if not has_llm(cfg):
        return {"mode": "offline", "online": False, "configured": False}
    try:
        model = ping(cfg)
        return {"mode": "live", "online": True, "configured": True, "model": model}
    except LLMError as e:
        return {"mode": "offline", "online": False, "configured": True, "error": str(e)}

@app.post("/api/grade")
def live_grade(req: GradeReq, background: BackgroundTasks, cfg: LLMConfig = Depends(llm_cfg)):
    pid = "live-" + hashlib.sha1(req.text.encode()).hexdigest()[:8]
    p = Prompt(id=pid, source="live-demo", raw_text=req.text, tags=["live"],
               kind=req.kind, context=req.context)
    db.upsert_prompt(p)
    g = safe_grade(p, cfg)
    db.save_grading(g)
    db.add_audit(AuditEntry(prompt_id=pid, action="graded", grade=g.grade,
                            detail=f"live; {len(g.risks_found)} risk(s)"))
    background.add_task(webhooks.emit, "asset.graded",
                        {"prompt_id": pid, "grade": g.grade, "kind": p.kind,
                         "risks": len(g.risks_found), "source": p.source})
    return _row(pid)

@app.post("/api/remediate/{pid}")
def live_remediate(pid: str, background: BackgroundTasks, cfg: LLMConfig = Depends(llm_cfg)):
    p = db.get_prompt(pid)
    if not p:
        raise HTTPException(404)
    fixed, g = safe_remediate(p, cfg)
    db.upsert_prompt(fixed); db.save_grading(g)
    db.add_audit(AuditEntry(prompt_id=pid, action="remediated", grade=g.grade, detail="rewrite+re-judge"))
    background.add_task(webhooks.emit, "asset.remediated",
                        {"prompt_id": pid, "grade": g.grade, "kind": fixed.kind})
    return _row(pid)

class OverrideReq(BaseModel):
    prompt_id: str
    to_grade: str
    reason: str

@app.post("/api/override")
def override(req: OverrideReq, background: BackgroundTasks):
    cur = db.latest_grading(req.prompt_id)
    if not cur:
        raise HTTPException(404)
    changed = apply_override(db, Override(prompt_id=req.prompt_id, from_grade=cur.grade,
                                          to_grade=req.to_grade, reason=req.reason))
    background.add_task(webhooks.emit, "asset.overridden",
                        {"prompt_id": req.prompt_id, "from_grade": cur.grade,
                         "to_grade": req.to_grade, "recalibrated": len(changed)})
    return {"changed": changed, "count": len(changed)}

class ReuseReq(BaseModel):
    text: str
    kind: str | None = None

@app.post("/api/reuse")
def reuse_matches(req: ReuseReq):
    """P5 reuse surface: top-3 KEEP prior artifacts most similar to a new task's text."""
    prompts = db.list_prompts()
    gradings = {p.id: g for p in prompts if (g := db.latest_grading(p.id))}
    hits = reuse.find_similar(req.text, prompts, gradings, top_n=3,
                              only_grade="KEEP", kind=req.kind)
    by_id = {p.id: p for p in prompts}
    matches = []
    for h in hits:
        p = by_id[h["prompt_id"]]
        g = gradings.get(p.id)
        matches.append({"prompt": p.model_dump(),
                        "grading": g.model_dump() if g else None,
                        "score": h["score"]})
    return {"matches": matches}

@app.get("/api/analytics")
def capability_analytics():
    """P5 capability analytics: composition, duplicates, coverage gaps, growth."""
    prompts = db.list_prompts()
    gradings = {p.id: g for p in prompts if (g := db.latest_grading(p.id))}
    return analytics.capability_report(prompts, gradings, db.list_audit())
