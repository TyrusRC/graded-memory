# CLAUDE.md

The canonical, cross-agent project guide is **[AGENTS.md](AGENTS.md)** — read it first for
setup commands, architecture, conventions, and the safety rules, and follow it exactly.

Project invariants worth repeating:

- The **deterministic core is the product's spine** — never make grading, reuse, or
  analytics depend on an LLM key. The LLM is additive only, and every prompt is redacted
  before any model call.
- **Synthetic data only.** Keep the backend test suite (`pytest`) and the frontend build
  (`npm run build`) green before considering a change done.
