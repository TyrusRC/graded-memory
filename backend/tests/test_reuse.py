from app.models import Prompt, Grading, RubricScores
from app.reuse import similarity, find_similar


def _p(pid: str, text: str, kind: str = "prompt") -> Prompt:
    return Prompt(id=pid, source=f"{pid}.md", raw_text=text, tags=["t"], kind=kind)


def _g(pid: str, grade: str) -> Grading:
    return Grading(prompt_id=pid, grade=grade,
                   rubric=RubricScores(clarity=5, context=4, output_quality=5, safety=5),
                   rationale="ok")


def test_similarity_identical_is_one():
    assert similarity("summarize the support ticket", "summarize the support ticket") == 1.0


def test_similarity_disjoint_is_zero():
    assert similarity("summarize support ticket", "deploy fraud scoring model") == 0.0


def test_similarity_ignores_stopwords():
    # stopwords ("the", "a", "of") should not inflate overlap
    assert similarity("draft a refund reply", "draft the refund reply") == 1.0


def test_similarity_partial_overlap_between_zero_and_one():
    s = similarity("summarize the support ticket in bullets",
                   "summarize the fraud alert in bullets")
    assert 0.0 < s < 1.0


def test_find_similar_ranks_and_filters_to_keep():
    prompts = [
        _p("a", "summarize the support ticket into three concise bullet points"),
        _p("b", "summarize the support case into three short bullet points"),
        _p("c", "deploy the fraud scoring service to production"),
    ]
    gradings = {"a": _g("a", "KEEP"), "b": _g("b", "REVISE"), "c": _g("c", "KEEP")}
    out = find_similar("summarize the support ticket into concise bullets", prompts, gradings)
    ids = [m["prompt_id"] for m in out]
    assert "b" not in ids           # filtered out (not KEEP)
    assert "a" in ids               # KEEP + similar
    assert all(m["score"] > 0 for m in out)


def test_find_similar_excludes_self():
    query = "reconcile the vendor ledger against the bank statement summary"
    prompts = [_p("a", query)]
    gradings = {"a": _g("a", "KEEP")}
    assert find_similar(query, prompts, gradings) == []


def test_find_similar_kind_filter():
    prompts = [
        _p("a", "onboard a new data analyst with warehouse access", kind="workflow"),
        _p("b", "onboard a new data analyst with warehouse access help", kind="prompt"),
    ]
    gradings = {"a": _g("a", "KEEP"), "b": _g("b", "KEEP")}
    out = find_similar("onboard a new analyst with warehouse access", prompts, gradings,
                       kind="workflow")
    assert [m["prompt_id"] for m in out] == ["a"]


def test_find_similar_top_n_and_order():
    prompts = [
        _p("a", "summarize the support ticket into three concise bullet points"),
        _p("b", "summarize the ticket into bullet points"),
        _p("c", "summarize the support ticket"),
        _p("d", "write friendly release notes for customers"),
    ]
    gradings = {k: _g(k, "KEEP") for k in ("a", "b", "c", "d")}
    out = find_similar("summarize the support ticket into concise bullet points",
                       prompts, gradings, top_n=2)
    assert len(out) == 2
    assert out[0]["score"] >= out[1]["score"]
