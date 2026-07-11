from app.models import Prompt, Grading, RubricScores, AuditEntry
from app.analytics import capability_report


def _p(pid: str, text: str, tags: list[str], kind: str = "prompt") -> Prompt:
    return Prompt(id=pid, source=f"{pid}.md", raw_text=text, tags=tags, kind=kind)


def _g(pid: str, grade: str) -> Grading:
    return Grading(prompt_id=pid, grade=grade,
                   rubric=RubricScores(clarity=5, context=4, output_quality=5, safety=5),
                   rationale="ok")


def _fixture():
    prompts = [
        _p("a", "summarize the support ticket into three concise bullet points", ["support"]),
        _p("b", "summarize the support ticket into three short bullet points", ["support"]),
        _p("c", "onboard a new data analyst with warehouse and dashboard access",
           ["onboarding"], kind="workflow"),
        _p("d", "route the incoming support ticket to the right queue", ["support"], kind="agent"),
        _p("e", "look up the customer and export the full accounts table", ["fraud"]),
    ]
    gradings = {
        "a": _g("a", "KEEP"), "b": _g("b", "KEEP"), "c": _g("c", "KEEP"),
        "d": _g("d", "REVISE"), "e": _g("e", "RETIRE"),
    }
    audit = [
        AuditEntry(prompt_id="a", action="graded", grade="KEEP", ts="2026-07-10T09:00:00+00:00"),
        AuditEntry(prompt_id="b", action="graded", grade="KEEP", ts="2026-07-10T10:00:00+00:00"),
        AuditEntry(prompt_id="c", action="graded", grade="KEEP", ts="2026-07-11T08:00:00+00:00"),
        AuditEntry(prompt_id="e", action="override", grade="RETIRE", ts="2026-07-11T09:00:00+00:00"),
    ]
    return prompts, gradings, audit


def test_by_kind_counts_all_three_kinds():
    prompts, gradings, audit = _fixture()
    rep = capability_report(prompts, gradings, audit)
    assert rep["by_kind"] == {"prompt": 3, "workflow": 1, "agent": 1}


def test_by_tag_sorted_desc_with_grade_breakdown():
    prompts, gradings, audit = _fixture()
    rep = capability_report(prompts, gradings, audit)
    tags = rep["by_tag"]
    assert tags[0]["tag"] == "support" and tags[0]["count"] == 3
    support = next(r for r in tags if r["tag"] == "support")
    assert support["keep"] == 2 and support["revise"] == 1 and support["retire"] == 0
    counts = [r["count"] for r in tags]
    assert counts == sorted(counts, reverse=True)


def test_duplicates_cluster_near_duplicate_pair():
    prompts, gradings, audit = _fixture()
    rep = capability_report(prompts, gradings, audit)
    dups = rep["duplicates"]
    assert len(dups) == 1
    members = {m["prompt_id"] for m in dups[0]["members"]}
    assert members == {"a", "b"}
    assert dups[0]["score"] >= 0.6


def test_growth_grouped_by_date_asc():
    prompts, gradings, audit = _fixture()
    rep = capability_report(prompts, gradings, audit)
    # only action=="graded" counted; override on 07-11 is excluded
    assert rep["growth"] == [
        {"date": "2026-07-10", "graded_count": 2},
        {"date": "2026-07-11", "graded_count": 1},
    ]


def test_coverage_gaps_are_tags_without_keep():
    prompts, gradings, audit = _fixture()
    rep = capability_report(prompts, gradings, audit)
    # fraud has only a RETIRE -> gap; support/onboarding have KEEP -> not gaps
    assert "fraud" in rep["coverage_gaps"]
    assert "support" not in rep["coverage_gaps"]
    assert "onboarding" not in rep["coverage_gaps"]
