# Graded Memory

A quality-and-safety gate for an organization's AI prompts. It grades each prompt
KEEP / REVISE / RETIRE, quarantines the unsafe ones, and keeps an append-only record
of every grade and human override — so inherited prompts are trustworthy on day one
and there is evidence they were reviewed before reuse.

Personal project. Synthetic data only. Runs offline with no API key.

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

**Backend** — Python (>= 3.11), FastAPI, SQLite, Google Gemini via `google-genai`.

```
backend/app/
  collector.py     discover prompts from a source tree
  risk_scan.py     deterministic scanner (regex + entropy) + redaction
  judge.py         LLM rubric grade, grounded by the scanner, with the safety gate
  offline_judge.py deterministic grader (no API key)
  live.py          live grade/remediate with automatic offline fallback
  remediation.py   rewrite an unsafe prompt and re-grade
  calibration.py   apply a human override and recalibrate similar prompts
  control_map.py   map a verdict + risks to named controls
  db.py            SQLite persistence + audit log
  main.py          FastAPI routes
```

**Frontend** — React, Vite, TypeScript, Tailwind. English / Vietnamese.

## Run

No API key is required. The offline grader is deterministic and seeds the full
library; live endpoints fall back to it automatically on any API error.

Backend:

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python scripts/seed_offline.py     # seeds 26 synthetic prompts (16 KEEP / 5 REVISE / 5 RETIRE)
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173, proxies /api to :8000
```

Live grading with a real model is optional. Copy `backend/.env.example` to
`backend/.env` and set `GEMINI_API_KEY`. The key is read only from `.env`, which is
gitignored.

## API

```
GET  /api/library                library with grades
GET  /api/newhire                KEEP-only prompts (safe to hand off)
GET  /api/prompt/{id}            prompt detail + audit trail
GET  /api/audit                  audit log
GET  /api/audit/export.csv       audit log as CSV
GET  /api/calibration            learned calibration rules
POST /api/grade                  grade a pasted prompt
POST /api/remediate/{id}         rewrite and re-grade
POST /api/override               human override + recalibrate
```

## Tests

```bash
cd backend && . .venv/bin/activate && python -m pytest      # 28 tests
```

Frontend type-check and build:

```bash
cd frontend && npm run build
```

## Status

Built: the grade / remediate / reuse loop, the four-dimension rubric with per-dimension
reasoning, the deterministic safety gate and quarantine, redact-before-model, the
append-only audit log mapped to a named control, human override with recalibration,
and English/Vietnamese UI.

Not yet built: measured judge reliability on a labeled evaluation set, automatic
outcome capture, verdict expiration, and CI-level enforcement.

## Data and safety

All prompts and credentials in this repo are synthetic fixtures. The string
`AKIAIOSFODNN7EXAMPLE` is AWS's public documentation example key, used as a deliberate
unsafe test case — it is not a real credential. Do not put real secrets in the seed
data or the scanner.

## License

See [LICENSE](LICENSE).
