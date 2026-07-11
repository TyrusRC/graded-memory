import { useEffect, useState } from "react";
import type { Row } from "../types";
import { api } from "../api";
import { Spinner } from "./ui";
import { useT } from "../i18n";

function firstLine(text: string): string {
  const line = text.split("\n").find((l) => l.trim().length > 0) ?? "";
  return line.trim();
}

export default function NewHire({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const t = useT();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .newhire()
      .then(setRows)
      .catch((e) =>
        setError(e instanceof Error ? e.message : t("nh.load_failed")),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div className="panel border-keep/25 p-8 text-center">
        <p className="eyebrow mb-3">{t("nh.certified")}</p>
        <p className="text-2xl font-semibold text-paper sm:text-3xl">
          {t("nh.day_one")}{" "}
          <span className="font-mono text-keep">{rows.length}</span>{" "}
          {t("nh.verified_safe")}{" "}
          <span className="font-mono text-keep">0</span> {t("nh.leaks")}
        </p>
        <p className="mt-2 text-sm text-muted">{t("nh.everything_below")}</p>
      </div>

      {loading ? (
        <p className="flex items-center justify-center gap-2 py-12 text-sm text-muted">
          <Spinner /> {t("common.loading")}
        </p>
      ) : error ? (
        <p className="py-12 text-center text-sm text-retire">{error}</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {rows.map((row) => (
            <button
              key={row.prompt.id}
              onClick={() => onSelect(row.prompt.id)}
              className="panel flex w-full min-w-0 flex-col items-start gap-1.5 p-4 text-left transition hover:border-keep/40"
            >
              <span className="w-full truncate font-mono text-xs text-keep/80">
                {row.prompt.source}
              </span>
              <span className="w-full break-words text-sm text-paper/90">
                {firstLine(row.prompt.raw_text)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
