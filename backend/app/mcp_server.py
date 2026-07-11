"""Model Context Protocol (MCP) server — exposes Graded Memory's deterministic core as
agent-callable tools, so any MCP client (Claude, IDE agents, internal agents) can grade
an AI asset, find the org's verified prior art, and see capability gaps mid-task.

No LLM key required: all three tools run on the deterministic offline core, so they work
anywhere and never leak a secret to an external model.

Run (stdio transport):  python -m app.mcp_server
Install first:           pip install ".[mcp]"
"""
from __future__ import annotations
import os
import re
from mcp.server.fastmcp import FastMCP
from app.models import Prompt
from app.offline_judge import offline_grade
from app.reuse import find_similar
from app.analytics import capability_report
from app.risk_scan import redact
from app.db import DB

_KINDS = ("prompt", "workflow", "agent")

mcp = FastMCP("graded-memory")
# Point at the seeded DB. Set GM_DB to an absolute path so the server works from any
# working directory (e.g. when launched by a Claude/Codex MCP client that doesn't set cwd).
_db = DB(os.environ.get("GM_DB", "graded.sqlite"))
_db.init()


def _gradings(prompts: list[Prompt]) -> dict:
    return {p.id: g for p in prompts if (g := _db.latest_grading(p.id))}


@mcp.tool()
def grade_asset(text: str, kind: str = "prompt") -> dict:
    """Grade an AI asset (prompt / workflow / agent config) KEEP, REVISE, or RETIRE on
    clarity, context, output quality, and safety. Deterministic, no API key, no side
    effects. Returns the verdict, rubric scores, rationale, any risks found (secrets,
    PII, unsafe or exfiltrating actions), and mapped governance controls."""
    safe_kind = kind if kind in _KINDS else "prompt"
    g = offline_grade(Prompt(id="mcp", source="mcp", raw_text=text, kind=safe_kind))
    return {
        "grade": g.grade,
        "rubric": g.rubric.model_dump(),
        "rationale": g.rationale,
        "risks": [r.model_dump() for r in g.risks_found],
        "control_map": g.control_map,
    }


@mcp.tool()
def remediate_asset(text: str, kind: str = "prompt") -> dict:
    """Make an unsafe asset safe: mask secrets, PII, and pasted source code to
    placeholders, then re-grade — deterministically, no key, no external call. Use this
    to fix a risky prompt before running or storing it. Returns the sanitized text, the
    new verdict, the rationale, and any risk that remains."""
    safe_kind = kind if kind in _KINDS else "prompt"
    sanitized = redact(text)
    g = offline_grade(Prompt(id="mcp", source="mcp", raw_text=sanitized, kind=safe_kind))
    return {
        "remediated_text": sanitized,
        "grade": g.grade,
        "rationale": g.rationale,
        "risks_remaining": [r.model_dump() for r in g.risks_found],
    }


@mcp.tool()
def find_prior_art(text: str, kind: str | None = None, top_n: int = 3) -> list[dict]:
    """Find the organization's verified (KEEP-graded) prior art most similar to a task —
    'has the org already solved this?' Reuse before rebuilding. Returns matches with
    source, kind, similarity score (0..1), and a text preview."""
    prompts = _db.list_prompts()
    hits = find_similar(text, prompts, _gradings(prompts),
                        top_n=max(1, top_n), only_grade="KEEP", kind=kind)
    by_id = {p.id: p for p in prompts}
    return [{"source": by_id[h["prompt_id"]].source,
             "kind": by_id[h["prompt_id"]].kind,
             "score": round(h["score"], 3),
             "preview": by_id[h["prompt_id"]].raw_text[:500]}
            for h in hits]


@mcp.tool()
def search_memory(query: str, kind: str | None = None, grade: str | None = None,
                  limit: int = 10) -> list[dict]:
    """Search the organization's AI memory by keyword, to browse or audit what exists.
    Optionally filter by kind (prompt/workflow/agent) and grade (KEEP/REVISE/RETIRE).
    Ranked by keyword overlap; returns source, kind, grade, and a preview. (Use
    find_prior_art instead when matching a new task to reusable prior work.)"""
    terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 1}
    prompts = _db.list_prompts()
    gradings = _gradings(prompts)
    scored: list[tuple[int, dict]] = []
    for p in prompts:
        if kind and p.kind != kind:
            continue
        g = gradings.get(p.id)
        if grade and (not g or g.grade != grade):
            continue
        hay = f"{p.source} {p.raw_text}".lower()
        hits = sum(1 for t in terms if t in hay)
        if hits:
            scored.append((hits, {"source": p.source, "kind": p.kind,
                                  "grade": g.grade if g else None,
                                  "preview": p.raw_text[:300]}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:max(1, limit)]]


@mcp.tool()
def capability_gaps() -> dict:
    """Report where the org's AI capability is duplicated or missing: near-duplicate
    asset clusters worth consolidating, tags with no certified (KEEP) asset, and the
    asset count by kind."""
    prompts = _db.list_prompts()
    rep = capability_report(prompts, _gradings(prompts), _db.list_audit())
    return {"duplicates": rep["duplicates"],
            "coverage_gaps": rep["coverage_gaps"],
            "by_kind": rep["by_kind"]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
