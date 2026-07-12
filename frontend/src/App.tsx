import { useEffect, useMemo, useState } from "react";
import type { Row } from "./types";
import { api } from "./api";
import Library from "./components/Library";
import PromptDetail from "./components/PromptDetail";
import Governance from "./components/Governance";
import Calibration from "./components/Calibration";
import NewHire from "./components/NewHire";
import Capability from "./components/Capability";
import LlmSettings from "./components/LlmSettings";
import { Spinner } from "./components/ui";
import { useT, useLang, type Lang } from "./i18n";

type Tab =
  | "library"
  | "prompt"
  | "governance"
  | "calibration"
  | "newhire"
  | "capability";

const TAB_IDS: Tab[] = [
  "library",
  "prompt",
  "governance",
  "calibration",
  "newhire",
  "capability",
];

const LANGS: Lang[] = ["en", "vi"];

export default function App() {
  const t = useT();
  const { lang, setLang } = useLang();
  const [tab, setTab] = useState<Tab>("library");
  const [rows, setRows] = useState<Row[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .library()
      .then(setRows)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load library"),
      )
      .finally(() => setLoading(false));
  }, []);

  function upsertRow(row: Row) {
    setRows((prev) => {
      const idx = prev.findIndex((r) => r.prompt.id === row.prompt.id);
      if (idx === -1) return [row, ...prev];
      const next = [...prev];
      next[idx] = row;
      return next;
    });
  }

  function selectPrompt(id: string) {
    setSelectedId(id);
    setTab("prompt");
  }

  // After a live grade, jump to the result so it's always visible — otherwise a
  // KEEP verdict sorts to the bottom of the weakest-first library and looks like
  // nothing happened.
  function handleGraded(row: Row) {
    upsertRow(row);
    selectPrompt(row.prompt.id);
  }

  const view = useMemo(() => {
    switch (tab) {
      case "library":
        return (
          <Library rows={rows} onSelect={selectPrompt} onGraded={handleGraded} />
        );
      case "prompt":
        return <PromptDetail id={selectedId} onRefreshed={upsertRow} />;
      case "governance":
        return <Governance />;
      case "calibration":
        return <Calibration rows={rows} />;
      case "newhire":
        return <NewHire onSelect={selectPrompt} />;
      case "capability":
        return <Capability />;
    }
  }, [tab, rows, selectedId]);

  return (
    <div className="min-h-full bg-ink text-paper">
      <header className="sticky top-0 z-10 border-b border-rule bg-ink/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="text-lg font-semibold tracking-tight text-seal">
            ◈ Graded Memory
          </span>
          <nav className="flex flex-wrap gap-1">
            {TAB_IDS.filter((id) => id !== "prompt" || selectedId).map((id) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className="tab"
                data-active={tab === id}
              >
                {t(`nav.${id}`)}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LlmSettings />
            {LANGS.map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className="btn-ghost"
                data-active={lang === l}
                aria-label={l === "en" ? "English" : "Tiếng Việt"}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1100px] px-4 py-8">
        {loading ? (
          <p className="flex items-center justify-center gap-2 py-20 text-sm text-muted">
            <Spinner /> {t("app.loading_library")}
          </p>
        ) : error ? (
          <div className="panel border-retire/40 p-4 text-sm text-retire">
            {error}
          </div>
        ) : (
          view
        )}
      </main>
    </div>
  );
}
