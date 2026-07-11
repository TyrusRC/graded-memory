"""Deterministic capability analytics (NO LLM) — P5 "where capability is growing,
duplicated, or missing." Aggregates prompts, latest gradings, and the audit log into
a single report the dashboard renders: composition by kind/tag, duplicate clusters to
consolidate, coverage gaps (capability missing), and graded-per-day growth."""
from __future__ import annotations
from itertools import combinations
from app.models import Prompt, Grading, AuditEntry
from app.reuse import similarity

_DUP_THRESHOLD = 0.6


def _duplicate_clusters(prompts: list[Prompt]) -> list[dict]:
    # Connected components over prompt pairs with similarity >= threshold.
    parent = {p.id: p.id for p in prompts}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges: dict[tuple[str, str], float] = {}
    for a, b in combinations(prompts, 2):
        s = similarity(a.raw_text, b.raw_text)
        if s >= _DUP_THRESHOLD:
            edges[(a.id, b.id)] = s
            parent[find(a.id)] = find(b.id)

    by_id = {p.id: p for p in prompts}
    groups: dict[str, list[str]] = {}
    for pid in parent:
        groups.setdefault(find(pid), []).append(pid)

    clusters: list[dict] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        member_set = set(members)
        scores = [s for (x, y), s in edges.items() if x in member_set and y in member_set]
        avg = sum(scores) / len(scores) if scores else 0.0
        clusters.append({
            "members": [{"prompt_id": m, "source": by_id[m].source} for m in members],
            "score": round(avg, 4),
        })
    clusters.sort(key=lambda c: c["score"], reverse=True)
    return clusters


def capability_report(prompts: list[Prompt], gradings: dict[str, Grading],
                      audit: list[AuditEntry]) -> dict:
    by_kind = {"prompt": 0, "workflow": 0, "agent": 0}
    for p in prompts:
        by_kind[p.kind] = by_kind.get(p.kind, 0) + 1

    tag_rows: dict[str, dict] = {}
    for p in prompts:
        g = gradings.get(p.id)
        for tag in p.tags:
            row = tag_rows.setdefault(tag, {"tag": tag, "count": 0, "keep": 0,
                                            "revise": 0, "retire": 0})
            row["count"] += 1
            if g:
                if g.grade == "KEEP":
                    row["keep"] += 1
                elif g.grade == "REVISE":
                    row["revise"] += 1
                elif g.grade == "RETIRE":
                    row["retire"] += 1
    by_tag = sorted(tag_rows.values(), key=lambda r: r["count"], reverse=True)

    growth_map: dict[str, int] = {}
    for e in audit:
        if e.action == "graded" and e.ts:
            day = e.ts[:10]
            growth_map[day] = growth_map.get(day, 0) + 1
    growth = [{"date": d, "graded_count": n} for d, n in sorted(growth_map.items())]

    coverage_gaps = [r["tag"] for r in by_tag if r["keep"] == 0]

    return {
        "by_kind": by_kind,
        "by_tag": by_tag,
        "duplicates": _duplicate_clusters(prompts),
        "growth": growth,
        "coverage_gaps": coverage_gaps,
    }
