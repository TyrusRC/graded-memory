"""Collector agent — autonomously walks a source tree with tools and extracts prompt
artifacts. An OpenAI-compatible tool-calling loop drives the agentic behaviour: the
model calls list_files / read_file repeatedly (list -> read -> decide) until it is done,
then a final structured call normalizes what it found into Prompt rows. Exposing plain
Python functions as tools is the agentic core; runs against any OpenAI-compatible
provider (bring-your-own-key)."""
from __future__ import annotations
import os
import json
import hashlib
from pydantic import BaseModel
from app.llm import LLMConfig, build_client, json_complete, with_retry
from app.models import Prompt
from app.risk_scan import redact

_MAX_STEPS = 24     # backstop so a misbehaving model can't loop forever


class _FileTags(BaseModel):
    source: str
    tags: list[str] = []


class _Tagged(BaseModel):
    files: list[_FileTags]


def _pid(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}:{text[:64]}".encode()).hexdigest()[:12]


_TOOLS = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List files under the corpus root, optionally within a subdir.",
        "parameters": {"type": "object", "properties": {
            "subdir": {"type": "string", "description": "relative subdir, or empty for root"}}},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read one file from the corpus by its relative path (sensitive spans masked).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]},
    }},
]


def collect(root: str, cfg: LLMConfig | None = None) -> list[Prompt]:
    client, model = build_client(cfg)

    def list_files(subdir: str = "") -> str:
        base = os.path.join(root, subdir)
        out = []
        for dp, _, files in os.walk(base):
            for f in files:
                out.append(os.path.relpath(os.path.join(dp, f), root))
        return "\n".join(out) or "(empty)"

    def read_file(path: str) -> str:
        full = os.path.join(root, path)
        with open(full, encoding="utf-8", errors="replace") as fh:
            return redact(fh.read()[:8000])     # the offshore model never sees raw content

    dispatch = {"list_files": list_files, "read_file": read_file}

    # Agentic loop: the model decides which tool to call next and iterates until it
    # stops requesting tools (or the step backstop trips).
    messages: list[dict] = [{"role": "user", "content": (
        "You are collecting an organization's accumulated AI prompts and saved commands. "
        "Use list_files, then read each file with read_file, and identify every distinct "
        "prompt/command/agent-instruction artifact. Sensitive values are masked as ⟦…⟧ — that "
        "is expected. When done, reply with a short plain summary of how many artifacts you "
        "found and where.")}]
    for _ in range(_MAX_STEPS):
        resp = with_retry(lambda: client.chat.completions.create(
            model=model, messages=messages, tools=_TOOLS, temperature=0))
        msg = resp.choices[0].message
        if not msg.tool_calls:
            break
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            fn = dispatch.get(tc.function.name)
            try:
                args = json.loads(tc.function.arguments or "{}")
                result = fn(**args) if fn else f"unknown tool {tc.function.name}"
            except (ValueError, TypeError, OSError) as e:
                result = f"tool error: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result[:8000]})

    # Local pass: one prompt per file. RAW text is read locally and stored on-shore (so the
    # demo keeps the verbatim secret); only REDACTED text is sent for topical tagging.
    rels = [r for r in list_files().splitlines() if r != "(empty)"]
    raw_by_source: dict[str, str] = {}
    redacted_corpus: list[str] = []
    for rel in rels:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        raw_by_source[rel] = raw
        redacted_corpus.append(f"### {rel}\n{redact(raw)[:4000]}")

    tagged = json_complete(
        "Assign 1-3 short topical tags (e.g. support, fraud, onboarding, data) to each file. "
        "Sensitive spans are masked as ⟦…⟧ — tag by topic anyway. Return ONLY JSON: "
        '{"files": [{"source": "<relative path>", "tags": ["tag", ...]}]}',
        "\n\n".join(redacted_corpus), _Tagged, cfg)
    tags_by_source = {ft.source: ft.tags for ft in tagged.files}

    return [Prompt(id=_pid(rel, raw_by_source[rel]), source=rel,
                   raw_text=raw_by_source[rel], tags=tags_by_source.get(rel, []))
            for rel in rels]
