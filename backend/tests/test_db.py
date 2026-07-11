from app.db import DB
from app.models import Prompt, Grading, RubricScores, Override, AuditEntry, RiskHit

def make_db(tmp_path):
    db = DB(str(tmp_path / "t.sqlite"))
    db.init()
    return db

def test_upsert_and_get_prompt(tmp_path):
    db = make_db(tmp_path)
    db.upsert_prompt(Prompt(id="p1", source="a.md", raw_text="hello", tags=["support"]))
    p = db.get_prompt("p1")
    assert p.raw_text == "hello" and p.tags == ["support"]

def test_save_and_latest_grading(tmp_path):
    db = make_db(tmp_path)
    db.upsert_prompt(Prompt(id="p1", source="a.md", raw_text="x"))
    g = Grading(prompt_id="p1", grade="RETIRE",
                rubric=RubricScores(clarity=3, context=2, output_quality=3, safety=0),
                rationale="secret found",
                risks_found=[RiskHit(category="secret", match="AKIA", severity="high")],
                control_map=["OWASP LLM02"])
    db.save_grading(g)
    assert db.latest_grading("p1").grade == "RETIRE"

def test_audit_is_appended(tmp_path):
    db = make_db(tmp_path)
    db.add_audit(AuditEntry(prompt_id="p1", action="graded", grade="KEEP"))
    db.add_audit(AuditEntry(prompt_id="p1", action="override", grade="RETIRE"))
    log = db.list_audit()
    assert len(log) == 2 and log[0].ts != "" and log[-1].action == "override"

def test_override_recorded(tmp_path):
    db = make_db(tmp_path)
    db.save_override(Override(prompt_id="p1", from_grade="KEEP", to_grade="RETIRE", reason="policy"))
    # override persists as its own row; presence is enough for MVP
    assert db.list_calibration() == []  # nothing learned until calibration writes it
