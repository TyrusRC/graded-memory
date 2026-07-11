from app.db import DB
from app.calibration import similar_prompt_ids, apply_override
from app.models import Prompt, Grading, RubricScores, Override

def _seed(tmp_path):
    db = DB(str(tmp_path / "c.sqlite")); db.init()
    for pid, tags in [("a", ["fraud", "scoring"]), ("b", ["fraud", "risk"]), ("c", ["support"])]:
        db.upsert_prompt(Prompt(id=pid, source=f"{pid}.md", raw_text="x", tags=tags))
        db.save_grading(Grading(prompt_id=pid, grade="KEEP",
                                rubric=RubricScores(clarity=4, context=4, output_quality=4, safety=4),
                                rationale="ok"))
    return db

def test_similarity_by_tag_overlap(tmp_path):
    db = _seed(tmp_path)
    target = db.get_prompt("a")
    sims = similar_prompt_ids(db, target)
    assert "b" in sims and "c" not in sims and "a" not in sims

def test_override_recalibrates_similar(tmp_path):
    db = _seed(tmp_path)
    changed = apply_override(db, Override(prompt_id="a", from_grade="KEEP",
                                          to_grade="RETIRE", reason="fraud prompts are high-risk here"))
    assert "b" in changed
    assert db.latest_grading("b").grade == "RETIRE"      # learned appetite propagated
    assert db.latest_grading("c").grade == "KEEP"        # unrelated untouched
    assert db.list_calibration()                          # a rule was recorded
    actions = [a.action for a in db.list_audit()]
    assert "override" in actions and "recalibrated" in actions
