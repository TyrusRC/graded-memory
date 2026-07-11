import { useMemo, useState } from "react";
import type { Grade, Row } from "../types";
import { api } from "../api";
import { GradeBadge, RiskChip, Tag, Spinner } from "./ui";
import { useT } from "../i18n";

type Filter = "ALL" | Grade;

const FILTERS: Filter[] = ["ALL", "KEEP", "REVISE", "RETIRE"];

// Lower rank = more dangerous = surfaced first (RETIRE, REVISE, ungraded, KEEP;
// then by ascending safety score within a grade).
function riskRank(row: Row): number {
  const grade = row.grading?.grade;
  const base =
    grade === "RETIRE" ? 0 : grade === "REVISE" ? 1 : grade == null ? 2 : 3;
  const safety = row.grading?.rubric.safety ?? 5;
  return base * 10 + safety;
}

function Card({ row, onSelect }: { row: Row; onSelect: (id: string) => void }) {
  const { prompt, grading } = row;
  const showRisks =
    grading && (grading.grade === "RETIRE" || grading.grade === "REVISE");
  return (
    <button
      onClick={() => onSelect(prompt.id)}
      className="panel flex w-full min-w-0 flex-col items-start gap-3 p-4 text-left transition hover:border-rule-strong"
    >
      <div className="flex w-full items-start justify-between gap-2">
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted">
          {prompt.source}
        </span>
        <GradeBadge grade={grading?.grade ?? null} />
      </div>
      <p className="line-clamp-3 w-full break-words text-sm text-paper/90">
        {prompt.raw_text}
      </p>
      {prompt.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {prompt.tags.map((t) => (
            <Tag key={t}>{t}</Tag>
          ))}
        </div>
      )}
      {showRisks && grading.risks_found.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {grading.risks_found.map((r, i) => (
            <RiskChip key={i} category={r.category} severity={r.severity} />
          ))}
        </div>
      )}
    </button>
  );
}

export default function Library({
  rows,
  onSelect,
  onGraded,
}: {
  rows: Row[];
  onSelect: (id: string) => void;
  onGraded: (row: Row) => void;
}) {
  const t = useT();
  const [filter, setFilter] = useState<Filter>("ALL");
  const [query, setQuery] = useState("");
  const [text, setText] = useState("");
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matched = rows.filter((row) => {
      if (filter !== "ALL" && row.grading?.grade !== filter) return false;
      if (!q) return true;
      return (
        row.prompt.source.toLowerCase().includes(q) ||
        row.prompt.raw_text.toLowerCase().includes(q)
      );
    });
    // Weakest-safety-first: surface danger before green. A quiet, unexplained
    // KEEP is the most dangerous screen, so it sorts last.
    return [...matched].sort((a, b) => riskRank(a) - riskRank(b));
  }, [rows, filter, query]);

  async function gradeLive() {
    if (!text.trim() || grading) return;
    setGrading(true);
    setError(null);
    try {
      const row = await api.grade(text.trim());
      onGraded(row);
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("lib.grading_failed"));
    } finally {
      setGrading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="panel p-4">
        <h2 className="eyebrow mb-2">{t("lib.grade_new")}</h2>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("lib.paste_placeholder")}
          rows={3}
          className="well w-full resize-y p-3 font-mono text-sm"
        />
        <div className="mt-2 flex items-center gap-3">
          <button
            onClick={gradeLive}
            disabled={grading || !text.trim()}
            className="btn-primary"
          >
            {grading && <Spinner />}
            {grading ? t("lib.grading") : t("lib.grade_live")}
          </button>
          {error && <span className="text-sm text-retire">{error}</span>}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="btn-ghost"
              data-active={filter === f}
            >
              {f === "ALL" ? t("filter.all") : f}
            </button>
          ))}
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("lib.search_placeholder")}
          className="well ml-auto w-full max-w-xs px-3 py-1.5 text-sm"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted">
          {t("lib.no_match")}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((row) => (
            <Card key={row.prompt.id} row={row} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}
