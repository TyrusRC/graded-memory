# Graded Memory

**The capability layer that captures an organization's AI knowledge, certifies what's
safe, and hands it forward** — so individual learning becomes permanent organizational
capability. It captures prompts, workflows, and agent configs into one searchable
memory, grades each **KEEP / REVISE / RETIRE**, surfaces verified prior art when someone
starts a new task, maps where capability is growing / duplicated / missing, and keeps an
append-only record of every grade and human override.

Built for **Problem 5 — Organizational AI Memory** (AABW Founder Mode). Synthetic data
only. Runs fully offline with no API key.

**Live demo:** https://graded-memory.web.app · **API:** https://graded-memory-api.onrender.com

## The capability layer

- **Capture** — prompts, **workflows, and agent configs** as first-class assets, each
  able to carry a "why it worked / when to use it" note so the reasoning transfers too.
- **Certify** — every asset graded KEEP / REVISE / RETIRE; unsafe ones quarantined; a
  one-click remediation rewrites and re-grades.
- **Reuse** — start a task and the org's verified prior art surfaces instantly.
- **Capability map** — where AI capability is growing, duplicated (near-duplicate
  clusters), or missing (tags with no certified asset).
- **Hand forward** — a new hire inherits a clean, certified library on day one.
- **Compound** — each human override tunes the grader to the org's risk posture and
  re-grades every similar asset.

## How it works

1. **Discover** — prompts are collected from a source tree into one library.
2. **Scan (local)** — a deterministic scanner checks each prompt for secrets,
   proprietary source code, PII, and unsafe instructions. This runs on the original
   text, on-machine.
3. **Redact, then judge** — the text is redacted before it is sent to the model.
   An LLM scores it against a four-part rubric and assigns a grade. The scanner's
   findings are passed as categories only; raw secret values never leave the machine.
4. **Decide** — any high-severity risk forces RETIRE regardless of the model's grade.
   The model reasons; the policy decides safety.
5. **Record** — every grade, remediation, and override is written to an append-only
   audit log and mapped to a named control.
6. **Calibrate** — a human override is stored as a rule and re-grades similar prompts,
   tuning the grader to the org's risk posture.

## Grading

Four rubric dimensions, scored 0–5: **clarity**, **context**, **output quality**,
**safety**.

Verdicts:

- **KEEP** — safe and good to reuse as-is.
- **REVISE** — useful but needs a fix (vague, stale, or a fixable risk).
- **RETIRE** — quarantined; contains a serious risk or is unsafe.

Safety gate: if the scanner finds any **high-severity** risk (e.g. an AWS key, a
private key block, a DB URI with credentials), the verdict is forced to RETIRE and the
prompt is excluded from reuse — the model cannot override this.

The scanner covers: secret patterns (AWS keys, Slack tokens, private keys, JWTs,
credentialed DB URIs, hardcoded credentials), high-entropy strings, source-code
signatures, PII (email, phone, national ID, payment card), and unsafe instructions
(prompt-injection, destructive SQL, bulk data export, disabling controls).

## Data sovereignty

Detection happens locally on the original text. Only redacted text is sent to the
model, and scanner findings are described by category, never by raw value. This keeps
secrets and PII out of any offshore model call.

## Architecture

**Backend** — Python (>= 3.11), FastAPI, SQLite, and any OpenAI-compatible LLM via the
`openai` client. The LLM is bring-your-own-key and provider-agnostic, with one-click
presets for OpenAI, Google Gemini, Qwen, Groq, DeepSeek, Mistral, Together, and
OpenRouter (a universal gateway to Claude, Llama, and 300+ models) — plus a custom
option for any other endpoint incl. local Ollama/vLLM. With no key, grading, reuse, and
the capability map all run deterministically offline.

```
backend/app/
  collector.py     discover prompts/workflows/agents from a source tree
  risk_scan.py     deterministic scanner (regex + entropy) + redaction
  judge.py         LLM rubric grade, grounded by the scanner, with the safety gate
  offline_judge.py deterministic grader (no API key)
  live.py          live grade/remediate with automatic offline fallback
  remediation.py   rewrite an unsafe prompt and re-grade
  reuse.py         deterministic similarity — surface verified prior art
  analytics.py     capability map: coverage, duplicate clusters, gaps
  calibration.py   apply a human override and recalibrate similar prompts
  control_map.py   map a verdict + risks to named controls
  llm.py           OpenAI-compatible BYOK adapter + SSRF guard + health ping
  db.py            SQLite persistence + audit log
  main.py          FastAPI routes
```

**Frontend** — React, Vite, TypeScript, Tailwind; a Capability analytics view, a
bring-your-own-key panel with a live green/grey status dot, and English / Vietnamese UI.

## Run

No API key is required. The offline grader is deterministic and seeds the full
library; live endpoints fall back to it automatically on any API error.

Backend:

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python scripts/seed_offline.py     # seeds 34 synthetic assets (23 KEEP / 6 REVISE / 5 RETIRE)
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173, proxies /api to :8000
```

Live grading with a real model is optional and bring-your-own-key. Two ways to enable it:

- **Per-user, from the browser** — open the status control in the header (the green/grey
  dot), pick a provider, and paste your base URL / API key / model. The key stays in your
  browser and is sent only as a per-request header to grade; it is never stored or logged
  server-side. This is how the hosted demo stays free — no operator key required.
- **Operator-wide** — copy `backend/.env.example` to `backend/.env` and set `LLM_BASE_URL`,
  `LLM_API_KEY`, and `LLM_MODEL`. `.env` is gitignored.

Either way, prompts are redacted locally before any model call, and the deterministic
safety gate overrides the model on high-severity risks.

## API

```
GET  /api/library                library with grades
GET  /api/newhire                KEEP-only assets (safe to hand off)
GET  /api/prompt/{id}            asset detail + audit trail
GET  /api/audit                  audit log
GET  /api/audit/export.csv       audit log as CSV
GET  /api/calibration            learned calibration rules
GET  /api/analytics              capability map (by kind, coverage, duplicates, gaps)
GET  /api/llm/status             live provider health for the green dot
POST /api/reuse                  surface verified prior art for a task
POST /api/grade                  grade a pasted asset (optional kind + context)
POST /api/remediate/{id}         rewrite and re-grade
POST /api/override               human override + recalibrate
```

LLM config is passed per-request via `X-LLM-Base-Url` / `X-LLM-Api-Key` / `X-LLM-Model`
headers (bring-your-own-key) and is never stored server-side.

Because the backend is FastAPI, an interactive **OpenAPI** spec is served automatically
at `/docs` (Swagger UI) and `/openapi.json` — so a business can generate a client and
integrate against the API directly.

## Integration & enterprise

**Available today**

- **Self-hostable and fully offline.** The deterministic core (scan, grade, reuse,
  capability map) runs with no external calls and redacts before any model call — an
  on-prem / air-gapped deployment for regulated buyers and data-sovereignty regimes.
- **REST API + OpenAPI.** Integrate over HTTP; generate a client from `/openapi.json`.
- **Bring-your-own-key, provider-agnostic.** Point it at any OpenAI-compatible endpoint;
  keys are per-request and never stored.
- **Audit export + control mapping.** Append-only log (CSV export) mapped to EU AI Act /
  NIST AI RMF / SR 26-2 — the evidence an auditor asks for.
- **MCP server.** Exposes the deterministic core to any [Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
  client — five agent-callable tools: `grade_asset`, `remediate_asset`, `find_prior_art`,
  `search_memory`, `capability_gaps`. No key required. Run it:
  ```bash
  cd backend && pip install ".[mcp]" && python -m app.mcp_server
  ```
  Connect it to **Claude** (Desktop / Code) or **OpenAI Codex** — both read this server the
  same way. Claude Desktop (`claude_desktop_config.json`) or Cursor:
  ```json
  {
    "mcpServers": {
      "graded-memory": {
        "command": "/ABS/PATH/graded-memory/backend/.venv/bin/python",
        "args": ["-m", "app.mcp_server"],
        "env": { "GM_DB": "/ABS/PATH/graded-memory/backend/graded.sqlite" }
      }
    }
  }
  ```
  OpenAI Codex (`~/.codex/config.toml`):
  ```toml
  [mcp_servers.graded-memory]
  command = "/ABS/PATH/graded-memory/backend/.venv/bin/python"
  args = ["-m", "app.mcp_server"]
  env = { GM_DB = "/ABS/PATH/graded-memory/backend/graded.sqlite" }
  ```
  Codex also reads this repo's `AGENTS.md` natively, so it follows the project rules too.

**Roadmap toward enterprise integration** — all open-source and self-hostable, no paid dependencies

- **LLM-gateway guardrail** — a pre-call hook for the open-source, self-hosted
  [LiteLLM](https://docs.litellm.ai/docs/simple_proxy) proxy that grades and blocks
  unsafe prompts in-flight.
- **Multi-tenancy + RBAC** — org-scoped data on Postgres with role-based access, built
  in-app. Standards-based **SSO (OIDC/SAML)** via a self-hosted open-source identity
  provider (e.g. Keycloak / Authentik) — no paid identity vendor.
- **Capture connectors** — GitHub App (grade prompts in PRs), Confluence, Slack, Drive.
- **Judge reliability** — measured on a labeled evaluation set.

## Tests

```bash
cd backend && . .venv/bin/activate && python -m pytest      # 45 tests
```

Frontend type-check and build:

```bash
cd frontend && npm run build
```

## Status

Built: capture of prompts / workflows / agents as first-class assets with per-asset
context; the grade / remediate loop; the four-dimension rubric with per-dimension
reasoning; the deterministic safety gate and quarantine; redact-before-model; the
reuse (prior-art) surface; the capability map (coverage, duplicate clusters, gaps);
the append-only audit log mapped to named controls; human override with recalibration;
provider-agnostic bring-your-own-key with a live health indicator and offline fallback;
and English / Vietnamese UI. Deployed live (Firebase + Render), 45 tests green.

Not yet built: measured judge reliability on a labeled evaluation set, automatic
outcome capture, verdict expiration, versioning/lineage, and CI-level enforcement.

## Data and safety

All prompts and credentials in this repo are synthetic fixtures. The string
`AKIAIOSFODNN7EXAMPLE` is AWS's public documentation example key, used as a deliberate
unsafe test case — it is not a real credential. Do not put real secrets in the seed
data or the scanner.

## License

See [LICENSE](LICENSE).
