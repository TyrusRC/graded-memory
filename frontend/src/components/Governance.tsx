import { useEffect, useMemo, useState } from "react";
import type { AuditEntry } from "../types";
import { api, AUDIT_CSV_URL } from "../api";
import { GradeBadge, Spinner } from "./ui";
import { useT } from "../i18n";

export default function Governance() {
  const t = useT();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .audit()
      .then(setEntries)
      .catch((e) =>
        setError(e instanceof Error ? e.message : t("gov.load_failed")),
      )
      .finally(() => setLoading(false));
  }, []);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const e of entries) map.set(e.action, (map.get(e.action) ?? 0) + 1);
    return Array.from(map.entries());
  }, [entries]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="eyebrow">{t("gov.title")}</h2>
          <p className="mt-1 font-mono text-xs text-muted">
            {t("gov.events", { n: entries.length })}
            {counts.length > 0 && "  ·  "}
            {counts.map(([action, n], i) => (
              <span key={action}>
                {i > 0 && "   "}
                <span className="text-paper">{n}</span> {action}
              </span>
            ))}
          </p>
        </div>
        <a
          href={AUDIT_CSV_URL}
          target="_blank"
          rel="noreferrer"
          className="btn-primary"
        >
          {t("gov.export_csv")}
        </a>
      </div>

      {loading ? (
        <p className="flex items-center gap-2 py-12 text-sm text-muted">
          <Spinner /> {t("common.loading")}
        </p>
      ) : error ? (
        <p className="py-12 text-sm text-retire">{error}</p>
      ) : (
        <div className="panel overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="eyebrow border-b border-rule-strong">
                <th className="px-4 py-2 font-normal">{t("gov.col_prompt")}</th>
                <th className="px-4 py-2 font-normal">{t("gov.col_action")}</th>
                <th className="px-4 py-2 font-normal">{t("gov.col_grade")}</th>
                <th className="px-4 py-2 font-normal">{t("gov.col_detail")}</th>
                <th className="px-4 py-2 text-right font-normal">
                  {t("gov.col_timestamp")}
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr
                  key={e.id}
                  className="border-t border-rule hover:bg-ink-3"
                >
                  <td className="whitespace-nowrap px-4 py-2 text-muted">
                    {e.prompt_id}
                  </td>
                  <td className="px-4 py-2 text-paper">{e.action}</td>
                  <td className="px-4 py-2">
                    {e.grade ? (
                      <GradeBadge grade={e.grade} />
                    ) : (
                      <span className="text-muted-2">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2 font-sans text-muted">{e.detail}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-right text-muted-2">
                    {e.ts}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
