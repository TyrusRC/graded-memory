# CLAUDE.md

The canonical, cross-agent project guide is **[AGENTS.md](AGENTS.md)** — read it first for
setup commands, architecture, conventions, and the non-negotiable safety rules. Follow it
exactly. This file only adds Claude-specific emphasis.

- The user's global `~/.claude/CLAUDE.md` rules also apply and take precedence.
- The **deterministic core is the product's spine** — never make grading, reuse, or
  analytics depend on an LLM key. The LLM is additive only, and every prompt is redacted
  before any model call.
- **Synthetic data only**; keep the full backend test suite (`pytest`) and the frontend
  build (`npm run build`) green before claiming done.
- Commit as **TyrusRC <63230297+TyrusRC@users.noreply.github.com>**; ask before pushing.
