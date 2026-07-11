"""The MCP tools reuse the deterministic core, so an AI agent gets the same verdicts as
the dashboard. Skipped if the optional `mcp` extra isn't installed."""
import pytest

pytest.importorskip("mcp")
from app import mcp_server as m  # noqa: E402


def test_grade_asset_flags_secret_and_retires():
    g = m.grade_asset("connect using AKIAIOSFODNN7EXAMPLE to prod")
    assert g["grade"] == "RETIRE"
    assert any(r["category"] == "secret" for r in g["risks"])
    assert g["control_map"]                       # controls mapped


def test_grade_asset_clean_keeps():
    g = m.grade_asset("Summarize this support ticket in two sentences.")
    assert g["grade"] == "KEEP"


def test_grade_asset_tolerates_bad_kind():
    # An agent passing an unknown kind must not crash the tool.
    g = m.grade_asset("do a thing", kind="not-a-kind")
    assert g["grade"] in ("KEEP", "REVISE", "RETIRE")


def test_tool_return_shapes():
    art = m.find_prior_art("summarize a support ticket", top_n=3)
    assert isinstance(art, list)
    for a in art:
        assert {"source", "kind", "score", "preview"} <= set(a)
        assert 0.0 < a["score"] <= 1.0
    gaps = m.capability_gaps()
    assert {"duplicates", "coverage_gaps", "by_kind"} <= set(gaps)
