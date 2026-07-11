# AGENTS.md

Guidance for AI coding agents (Codex, Cursor, Copilot, Claude Code, Windsurf, …) working
in this repo. This is the canonical cross-tool project guide; `CLAUDE.md` defers to it.
For the product overview, see `README.md`.

**Graded Memory** is a capability layer that captures an organization's AI knowledge —
prompts, workflows, and agent configs — grades each **KEEP / REVISE / RETIRE**, surfaces
verified prior art, maps capability gaps, and keeps an auditable record. The core is
**deterministic**; the LLM is optional and bring-your-own-key.

## Setup & commands

Backend — Python ≥ 3.11, FastAPI + SQLite (run from `backend/`):
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"            # add ".[mcp]" to run the MCP server
python scripts/seed_offline.py     # seed the local DB (34 synthetic assets, no key)
uvicorn app.main:app --port 8000   # serve the API
python -m pytest -q                # run tests — MUST stay green
```
Frontend — React + Vite + TypeScript + Tailwind (run from `frontend/`):
```bash
npm install
npm run dev                        # http://localhost:5173, proxies /api to :8000
npm run build                      # tsc + production build — MUST pass
```
MCP server — optional integration (run from `backend/`):
```bash
pip install ".[mcp]" && python -m app.mcp_server
```

## Architecture

Backend `backend/app/`:
- `risk_scan.py` — deterministic scanner (regex + entropy) + `redact()`
- `offline_judge.py` — deterministic grader (no key); `judge.py` / `remediation.py` — LLM (optional)
- `reuse.py` — similarity → prior art; `analytics.py` — capability map (coverage, duplicates, gaps)
- `calibration.py` — human override → recalibrate similar; `control_map.py` — verdict → named controls
- `llm.py` — OpenAI-compatible BYOK adapter + SSRF guard + health ping
- `live.py` — live-then-offline orchestration; `db.py` — SQLite + audit log; `main.py` — FastAPI routes
- `mcp_server.py` — MCP tools (grade / remediate / find prior art / search / gaps)

Frontend `frontend/src/`: `components/{Library,PromptDetail,Capability,NewHire,Governance,Calibration,LlmSettings,ui}.tsx`, `api.ts`, `types.ts`, `i18n.tsx` (EN/VI).

## Conventions

- Match the existing style; keep modules small and single-responsibility. No large files.
- Backend: type hints + Pydantic models; **parameterized SQL only** (never string-built).
- Frontend: strict TS (`npm run build` must pass); **all user-facing strings go in `i18n.tsx`
  in both `en` and `vi`**. Verdict tokens KEEP/REVISE/RETIRE stay canonical English.
- Every feature/bugfix gets a test; run the full suite before claiming done.
- MCP tools: snake_case names, clear one-paragraph descriptions, keep the toolset small.

## Non-negotiables — safety & security

- The **deterministic safety gate must remain**: any high-severity risk forces RETIRE
  regardless of the model. Grading, reuse, and analytics must keep working **offline (no key)**.
- **Redact before any LLM call** (`redact()`), so raw secrets never leave the machine.
- **Synthetic data only.** `AKIAIOSFODNN7EXAMPLE` is AWS's public example key (a deliberate
  test fixture) — never add a real secret to seed data, tests, or code.
- User-supplied LLM base URLs must pass the SSRF guard (`is_safe_base_url`): https + public host.
- Never hardcode or commit secrets or `.env`. Never disable TLS verification. Avoid `eval`,
  `shell=True` with untrusted input, unsafe deserialization, and weak crypto.

## Git & deploy

- Branch off `main` for features; small commits with a clear *why*.
- Commit as **TyrusRC <63230297+TyrusRC@users.noreply.github.com>**. Do not add co-authors.
- Ask the user to review before pushing; never force-push or rewrite pushed history; never
  bypass hooks (`--no-verify`) unless asked.
- Deploy: frontend → Firebase Hosting (`graded-memory.web.app`); backend → Render
  (`graded-memory-api.onrender.com`, auto-deploys on push to `main`). The MCP server and the
  `mcp` extra are **not** part of the deploy. Frontend prod build reads `frontend/.env.production`.
