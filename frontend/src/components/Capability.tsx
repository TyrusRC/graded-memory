import { useEffect, useState } from "react";
import type { Analytics, Kind } from "../types";
import { api } from "../api";
import { KindBadge, Spinner, Tag } from "./ui";
import { useT } from "../i18n";

const KINDS: Kind[] = ["prompt", "workflow", "agent"];

// P5 analytics: read the org's AI capability at a glance — where it's growing,
// where it's duplicated, where it's missing.
export default function Capability() {
  const t = useT();
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .analytics()
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : t("cap.load_failed")),
      );
  }, []);

  if (error) {
    return <p className="py-16 text-center text-sm text-retire">{error}</p>;
  }

  if (!data) {
    return (
      <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
        <Spinner /> {t("common.loading")}
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-paper">{t("cap.title")}</h2>
        <p className="mt-1 text-sm text-muted">{t("cap.intro")}</p>
      </div>

      <section>
        <h3 className="eyebrow mb-3">{t("cap.by_kind")}</h3>
        <div className="grid grid-cols-3 gap-4">
          {KINDS.map((k) => (
            <div key={k} className="panel flex flex-col items-start gap-2 p-4">
              <KindBadge kind={k} />
              <span className="font-mono text-2xl text-paper">
                {data.by_kind[k] ?? 0}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="eyebrow mb-3">{t("cap.coverage")}</h3>
        {data.by_tag.length === 0 ? (
          <p className="text-sm text-muted">{t("lib.no_match")}</p>
        ) : (
          <div className="panel overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-rule text-left">
                  <th className="eyebrow p-3">{t("cap.col_tag")}</th>
                  <th className="eyebrow p-3">{t("cap.col_total")}</th>
                  <th className="eyebrow p-3 text-keep">KEEP</th>
                  <th className="eyebrow p-3 text-revise">REVISE</th>
                  <th className="eyebrow p-3 text-retire">RETIRE</th>
                </tr>
              </thead>
              <tbody>
                {data.by_tag.map((row) => (
                  <tr key={row.tag} className="border-b border-rule/50">
                    <td className="p-3">
                      <Tag>{row.tag}</Tag>
                    </td>
                    <td className="p-3 font-mono text-paper">{row.count}</td>
                    <td className="p-3 font-mono text-keep">{row.keep}</td>
                    <td className="p-3 font-mono text-revise">{row.revise}</td>
                    <td className="p-3 font-mono text-retire">{row.retire}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h3 className="eyebrow mb-1">{t("cap.duplicates")}</h3>
        <p className="mb-3 text-xs text-muted">{t("cap.duplicates_note")}</p>
        {data.duplicates.length === 0 ? (
          <p className="text-sm text-muted">{t("cap.duplicates_none")}</p>
        ) : (
          <ul className="space-y-2">
            {data.duplicates.map((cluster, i) => (
              <li key={i} className="panel border-revise/30 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="eyebrow">
                    {t("cap.match", { score: Math.round(cluster.score * 100) })}
                  </span>
                </div>
                <ul className="space-y-1">
                  {cluster.members.map((m) => (
                    <li
                      key={m.prompt_id}
                      className="font-mono text-xs text-muted"
                    >
                      {m.source}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="eyebrow mb-1">{t("cap.gaps")}</h3>
        <p className="mb-3 text-xs text-muted">{t("cap.gaps_note")}</p>
        {data.coverage_gaps.length === 0 ? (
          <p className="text-sm text-keep">{t("cap.gaps_none")}</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {data.coverage_gaps.map((tag) => (
              <span key={tag} className="tag text-retire">
                {tag}
              </span>
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="eyebrow mb-3">{t("cap.growth")}</h3>
        {data.growth.length === 0 ? (
          <p className="text-sm text-muted">{t("cap.growth_none")}</p>
        ) : (
          <ol className="space-y-2 border-l border-rule pl-4">
            {data.growth.map((g) => (
              <li key={g.date} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-sm bg-seal" />
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-mono text-xs text-muted-2">
                    {g.date}
                  </span>
                  <span className="text-paper/90">
                    {t("cap.graded_count", { n: g.graded_count })}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
