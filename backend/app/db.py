from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from app.models import Prompt, Grading, RubricScores, Override, AuditEntry, RiskHit

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class DB:
    def __init__(self, path: str = "graded.sqlite"):
        self.path = path

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def init(self) -> None:
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS prompts(
              id TEXT PRIMARY KEY, source TEXT, raw_text TEXT, tags TEXT,
              kind TEXT DEFAULT 'prompt', context TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS gradings(
              prompt_id TEXT, grade TEXT, rubric TEXT, rationale TEXT,
              risks TEXT, control_map TEXT, model TEXT, ts TEXT,
              foreseen TEXT DEFAULT '[]');
            CREATE TABLE IF NOT EXISTS overrides(
              prompt_id TEXT, from_grade TEXT, to_grade TEXT, reason TEXT, actor TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id TEXT, action TEXT,
              grade TEXT, detail TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS calibration(
              id INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT, rule TEXT, ts TEXT);
            """)
            # Migration: add foreseen_actions to a gradings table created before it existed.
            cols = {row["name"] for row in c.execute("PRAGMA table_info(gradings)")}
            if "foreseen" not in cols:
                c.execute("ALTER TABLE gradings ADD COLUMN foreseen TEXT DEFAULT '[]'")
            # Migration: add kind + context to a prompts table created before they existed.
            pcols = {row["name"] for row in c.execute("PRAGMA table_info(prompts)")}
            if "kind" not in pcols:
                c.execute("ALTER TABLE prompts ADD COLUMN kind TEXT DEFAULT 'prompt'")
            if "context" not in pcols:
                c.execute("ALTER TABLE prompts ADD COLUMN context TEXT DEFAULT ''")

    # --- prompts ---
    def upsert_prompt(self, p: Prompt) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO prompts"
                " (id, source, raw_text, tags, kind, context) VALUES (?,?,?,?,?,?)",
                (p.id, p.source, p.raw_text, json.dumps(p.tags), p.kind, p.context))

    def _prompt(self, r: sqlite3.Row) -> Prompt:
        return Prompt(id=r["id"], source=r["source"], raw_text=r["raw_text"],
                      tags=json.loads(r["tags"]), kind=r["kind"], context=r["context"])

    def get_prompt(self, pid: str) -> Prompt | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM prompts WHERE id=?", (pid,)).fetchone()
        return self._prompt(r) if r else None

    def list_prompts(self) -> list[Prompt]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM prompts").fetchall()
        return [self._prompt(r) for r in rows]

    # --- gradings ---
    def save_grading(self, g: Grading) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO gradings"
                " (prompt_id, grade, rubric, rationale, risks, control_map, model, ts, foreseen)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (g.prompt_id, g.grade, g.rubric.model_dump_json(), g.rationale,
                 json.dumps([r.model_dump() for r in g.risks_found]),
                 json.dumps(g.control_map), g.model, _now(),
                 json.dumps(g.foreseen_actions)))

    def latest_grading(self, pid: str) -> Grading | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM gradings WHERE prompt_id=? ORDER BY ts DESC LIMIT 1",
                          (pid,)).fetchone()
        if not r:
            return None
        return Grading(prompt_id=r["prompt_id"], grade=r["grade"],
                       rubric=RubricScores.model_validate_json(r["rubric"]),
                       rationale=r["rationale"],
                       risks_found=[RiskHit(**x) for x in json.loads(r["risks"])],
                       control_map=json.loads(r["control_map"]), model=r["model"],
                       foreseen_actions=json.loads(r["foreseen"] or "[]"))

    def list_latest_gradings(self) -> list[Grading]:
        return [g for p in self.list_prompts() if (g := self.latest_grading(p.id))]

    # --- overrides + calibration + audit ---
    def save_override(self, o: Override) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO overrides VALUES (?,?,?,?,?,?)",
                      (o.prompt_id, o.from_grade, o.to_grade, o.reason, o.actor, _now()))

    def save_calibration(self, pattern: str, rule: str) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO calibration(pattern, rule, ts) VALUES (?,?,?)",
                      (pattern, rule, _now()))

    def list_calibration(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM calibration ORDER BY ts").fetchall()]

    def add_audit(self, e: AuditEntry) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO audit_log(prompt_id, action, grade, detail, ts) VALUES (?,?,?,?,?)",
                      (e.prompt_id, e.action, e.grade, e.detail, _now()))

    def list_audit(self) -> list[AuditEntry]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
        return [AuditEntry(id=r["id"], prompt_id=r["prompt_id"], action=r["action"],
                           grade=r["grade"], detail=r["detail"], ts=r["ts"]) for r in rows]
