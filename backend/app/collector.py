"""Collector agent — autonomously walks a source tree with tools and extracts
prompt artifacts. Gemini AUTOMATIC FUNCTION CALLING drives the agentic loop
(list → read → decide); a final structured call normalizes what it found into
Prompt rows. Passing plain Python functions as `tools` is the agentic core."""
from __future__ import annotations
import os
import hashlib
from pydantic import BaseModel
from google.genai import types
from app.llm import get_client, MODEL, with_retry
from app.models import Prompt
from app.risk_scan import redact

class _FileTags(BaseModel):
    source: str
    tags: list[str] = []

class _Tagged(BaseModel):
    files: list[_FileTags]

def _pid(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}:{text[:64]}".encode()).hexdigest()[:12]

def collect(root: str, client=None) -> list[Prompt]:
    client = client or get_client()

    def list_files(subdir: str = "") -> str:
        """List files under the corpus root (optionally within a subdir)."""
        base = os.path.join(root, subdir)
        out = []
        for dp, _, files in os.walk(base):
            for f in files:
                out.append(os.path.relpath(os.path.join(dp, f), root))
        return "\n".join(out) or "(empty)"

    def read_file(path: str) -> str:
        """Read one file from the corpus by its relative path (sensitive spans masked)."""
        full = os.path.join(root, path)
        with open(full, encoding="utf-8", errors="replace") as fh:
            return redact(fh.read()[:8000])     # the offshore model never sees raw content

    # Agentic loop: Gemini calls list_files/read_file autonomously and loops
    # (automatic function calling is on by default when functions are passed).
    with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=("You are collecting an organization's accumulated AI prompts and saved "
                  "commands. Use list_files, then read each file, and identify every distinct "
                  "prompt/command/agent-instruction artifact. Sensitive values are masked as ⟦…⟧ — "
                  "that is expected. When done, reply with a short plain summary of how many "
                  "artifacts you found and where."),
        config=types.GenerateContentConfig(tools=[list_files, read_file]),
    ))

    # Local pass: one prompt per file. RAW text is read locally and stored on-shore
    # (so the demo keeps the verbatim secret); only REDACTED text is sent for tagging.
    rels = [r for r in list_files().splitlines() if r != "(empty)"]
    raw_by_source: dict[str, str] = {}
    redacted_corpus: list[str] = []
    for rel in rels:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        raw_by_source[rel] = raw
        redacted_corpus.append(f"### {rel}\n{redact(raw)[:4000]}")

    resp = with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=("Assign 1-3 short topical tags (e.g. support, fraud, onboarding, data) to each "
                  "file below. Sensitive spans are masked as ⟦…⟧ — tag by topic anyway.\n\n"
                  + "\n\n".join(redacted_corpus)),
        config={"response_mime_type": "application/json", "response_schema": _Tagged},
    ))
    tags_by_source = {ft.source: ft.tags for ft in resp.parsed.files}

    return [Prompt(id=_pid(rel, raw_by_source[rel]), source=rel,
                   raw_text=raw_by_source[rel], tags=tags_by_source.get(rel, []))
            for rel in rels]
