import { useEffect, useState } from "react";
import type { CalibrationRule, Grade, Row } from "../types";
import { api } from "../api";
import { GradeBadge, Spinner, StatusChip, Term } from "./ui";
import { useT } from "../i18n";

const GRADES: Grade[] = ["KEEP", "REVISE", "RETIRE"];

export default function Calibration({
  rows,
  onChanged,
}: {
  rows: Row[];
  onChanged: () => void;
}) {
  const t = useT();
  const [promptId, setPromptId] = useState("");
  const [grade, setGrade] = useState<Grade>("KEEP");
  const [reason, setReason] = useState("");
  const [rules, setRules] = useState<CalibrationRule[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = rows.find((r) => r.prompt.id === promptId);

  useEffect(() => {
    if (!promptId && rows.length > 0) setPromptId(rows[0].prompt.id);
  }, [rows, promptId]);

  function loadRules() {
    api.calibration().then(setRules).catch(() => {});
  }

  useEffect(loadRules, []);

  async function apply() {
    if (!promptId || submitting) return;
    setSubmitting(true);
    setError(null);
    setToast(null);
    try {
      const result = await api.override(promptId, grade, reason.trim());
      setToast(
        t("cal.toast", {
          count: result.count,
          noun: result.count === 1 ? "prompt" : "prompts",
        }),
      );
      setReason("");
      loadRules();
      onChanged();   // refresh library grades so the recalibration is visible immediately
    } catch (e) {
      setError(e instanceof Error ? e.message : t("cal.override_failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <p className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <StatusChip status="built" />
        <span>
          <Term term={t("cal.calibration_term")}>
            {t("cal.calibration_help")}
          </Term>{" "}
          {t("cal.built_note")}
        </span>
      </p>

      {toast && (
        <div className="panel border-keep/35 px-4 py-3 text-sm font-medium text-keep">
          {toast}
        </div>
      )}

      <section className="panel space-y-4 p-5">
        <h2 className="eyebrow">{t("cal.override_recalibrate")}</h2>
        <p className="text-sm leading-relaxed text-muted">{t("cal.how")}</p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="eyebrow mb-1 block">{t("cal.prompt")}</span>
            <select
              value={promptId}
              onChange={(e) => setPromptId(e.target.value)}
              className="well w-full px-3 py-2 text-sm"
            >
              {rows.map((r) => (
                <option key={r.prompt.id} value={r.prompt.id}>
                  {r.prompt.source}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-muted-2">
              {t("cal.add_hint")}
            </span>
          </label>

          <label className="block text-sm">
            <span className="eyebrow mb-1 block">{t("cal.new_grade")}</span>
            <select
              value={grade}
              onChange={(e) => setGrade(e.target.value as Grade)}
              className="well w-full px-3 py-2 text-sm"
            >
              {GRADES.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>
        </div>

        {selected && (
          <div className="well space-y-2 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs text-muted">
                {selected.prompt.source}
              </span>
              <span className="flex items-center gap-2">
                <span className="eyebrow">{t("cal.current_grade")}</span>
                <GradeBadge grade={selected.grading?.grade ?? null} />
              </span>
            </div>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs text-paper/90">
              {selected.prompt.raw_text}
            </pre>
          </div>
        )}

        <label className="block text-sm">
          <span className="eyebrow mb-1 block">{t("cal.reason")}</span>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("cal.reason_placeholder")}
            className="well w-full px-3 py-2 text-sm"
          />
        </label>

        <div className="flex items-center gap-3">
          <button
            onClick={apply}
            disabled={submitting || !promptId}
            className="btn-primary"
          >
            {submitting && <Spinner />}
            {submitting ? t("cal.applying") : t("cal.apply")}
          </button>
          {error && <span className="text-sm text-retire">{error}</span>}
        </div>
      </section>

      <section>
        <h3 className="eyebrow mb-3">{t("cal.learned_rules")}</h3>
        {rules.length === 0 ? (
          <p className="text-sm text-muted">{t("cal.no_rules")}</p>
        ) : (
          <ul className="space-y-2">
            {rules.map((r) => (
              <li key={r.id} className="panel p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <code className="tag text-seal">{r.pattern}</code>
                  <span className="font-mono text-xs text-muted-2">
                    {r.ts}
                  </span>
                </div>
                <p className="mt-1.5 text-paper/90">{r.rule}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
