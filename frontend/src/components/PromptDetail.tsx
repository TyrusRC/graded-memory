import { useEffect, useState } from "react";
import type { PromptDetailRow, Rubric, Row } from "../types";
import { api } from "../api";
import { GradeBadge, Spinner, Tag, Term } from "./ui";
import { useT } from "../i18n";

const RUBRIC_KEYS: (keyof Rubric)[] = [
  "clarity",
  "context",
  "output_quality",
  "safety",
];

function RubricBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(5, value)) * 20;
  return (
    <div>
      <div className="mb-1 flex justify-between">
        <span className="eyebrow">{label}</span>
        <span className="font-mono text-xs text-paper">{value}/5</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-sm bg-ink-3 ring-1 ring-rule">
        <div
          className="h-full bg-seal/70"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function PromptDetail({
  id,
  onRefreshed,
}: {
  id: string | null;
  onRefreshed: (row: Row) => void;
}) {
  const t = useT();
  const [data, setData] = useState<PromptDetailRow | null>(null);
  const [loading, setLoading] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(promptId: string) {
    setLoading(true);
    setError(null);
    try {
      setData(await api.prompt(promptId));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("pd.load_failed"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) load(id);
    else setData(null);
  }, [id]);

  async function remediate() {
    if (!id || remediating) return;
    setRemediating(true);
    setError(null);
    try {
      const row = await api.remediate(id);
      onRefreshed(row);
      await load(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("pd.remediation_failed"));
    } finally {
      setRemediating(false);
    }
  }

  if (!id) {
    return (
      <p className="py-16 text-center text-sm text-muted">
        {t("pd.select_prompt")}
      </p>
    );
  }

  if (loading && !data) {
    return (
      <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
        <Spinner /> {t("pd.loading")}
      </p>
    );
  }

  if (error && !data) {
    return <p className="py-16 text-center text-sm text-retire">{error}</p>;
  }

  if (!data) return null;

  const { prompt, grading, audit } = data;
  const isRetire = grading?.grade === "RETIRE";
  // Proof the app is not an LLM wrapper: a high-severity risk forces RETIRE via a
  // deterministic policy gate that overrides whatever the model returned (true in
  // both the live and offline paths). Surface who actually made the call.
  const highRisk = grading?.risks_found.find((r) => r.severity === "high");
  // Provenance of trust, shown honestly: a human "override" in the audit trail
  // means a named human adjudicated; otherwise the verdict is AI-graded only.
  const humanReviewed = audit.some((a) => a.action === "override");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-muted">{prompt.source}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {prompt.tags.map((t) => (
              <Tag key={t}>{t}</Tag>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <GradeBadge grade={grading?.grade ?? null} size="lg" />
          {grading && (
            <span className="eyebrow">
              {humanReviewed
                ? t("pd.human_reviewed")
                : t("pd.ai_graded_only", { model: grading.model })}
            </span>
          )}
        </div>
      </div>

      {isRetire && (
        <div className="panel border-retire/40 px-3 py-2 text-sm">
          <p className="text-retire">{t("pd.quarantined_line")}</p>
          {highRisk && (
            <p className="mt-1 font-mono text-xs text-muted-2">
              {t("pd.policy_forced", { category: highRisk.category })}
            </p>
          )}
          <p className="mt-1 text-muted">{t("pd.now_what_retire")}</p>
        </div>
      )}

      <pre className="well overflow-x-auto whitespace-pre-wrap p-4 font-mono text-sm">
        {prompt.raw_text}
      </pre>

      {grading && grading.grade === "REVISE" && (
        <div className="space-y-2">
          <p className="text-sm text-muted">{t("pd.now_what_revise")}</p>
          <div className="flex items-center gap-3">
            <button
              onClick={remediate}
              disabled={remediating}
              className="btn-primary"
            >
              {remediating && <Spinner />}
              {remediating ? t("pd.remediating") : t("pd.remediate")}
            </button>
            {error && <span className="text-sm text-retire">{error}</span>}
          </div>
        </div>
      )}

      {grading ? (
        <>
          <section className="panel grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            {RUBRIC_KEYS.map((key) => (
              <RubricBar
                key={key}
                label={t(`rubric.${key}`)}
                value={grading.rubric[key]}
              />
            ))}
          </section>

          <section>
            <h3 className="eyebrow mb-2">{t("pd.rationale")}</h3>
            <p className="text-sm leading-relaxed text-paper/90">
              {grading.rationale}
            </p>
          </section>

          {grading.risks_found.length > 0 && (
            <section>
              <h3 className="eyebrow mb-2">{t("pd.risks_found")}</h3>
              <ul className="space-y-2">
                {grading.risks_found.map((r, i) => (
                  <li key={i} className="panel p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-paper">
                        {r.category}
                      </span>
                      <span className="font-mono text-xs uppercase tracking-wide text-muted-2">
                        {r.severity}
                      </span>
                    </div>
                    <p className="mt-1 text-muted">{r.detail}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {grading.control_map.length > 0 && (
            <section>
              <h3 className="eyebrow mb-2">
                <Term term={t("pd.control_map")}>
                  {t("pd.control_map_help")}
                </Term>
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {grading.control_map.map((c) => (
                  <Tag key={c}>{c}</Tag>
                ))}
              </div>
            </section>
          )}
        </>
      ) : (
        <div className="panel px-3 py-2 text-sm">
          <p className="text-paper">{t("pd.cannot_certify")}</p>
          <p className="mt-1 text-muted">{t("pd.cannot_certify_help")}</p>
        </div>
      )}

      <section>
        <h3 className="eyebrow mb-3">{t("pd.audit_timeline")}</h3>
        {audit.length === 0 ? (
          <p className="text-sm text-muted">{t("pd.no_audit")}</p>
        ) : (
          <ol className="space-y-3 border-l border-rule pl-4">
            {audit.map((a) => (
              <li key={a.id} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-sm bg-seal" />
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-mono text-xs text-paper">
                    {a.action}
                  </span>
                  {a.grade && <GradeBadge grade={a.grade} />}
                  <span className="font-mono text-xs text-muted-2">
                    {a.ts}
                  </span>
                </div>
                {a.detail && (
                  <p className="mt-0.5 text-xs text-muted">{a.detail}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
