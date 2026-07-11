import { useEffect, useRef, useState } from "react";
import type { LlmStatus } from "../types";
import { api } from "../api";
import {
  loadLlmConfig,
  saveLlmConfig,
  PROVIDERS,
  providerIdFor,
  type LlmConfig,
} from "../llm";
import { Spinner } from "./ui";
import { useT } from "../i18n";

type DotState = "checking" | "online" | "offline" | "error";

function dotClass(state: DotState): string {
  switch (state) {
    case "online":
      return "bg-keep shadow-[0_0_6px] shadow-keep/70";
    case "error":
      return "bg-retire shadow-[0_0_6px] shadow-retire/70";
    case "checking":
      return "bg-revise animate-pulse";
    default:
      return "bg-muted-2";
  }
}

function toState(status: LlmStatus | null, checking: boolean): DotState {
  if (checking) return "checking";
  if (!status) return "offline";
  if (status.online) return "online";
  return status.configured ? "error" : "offline";
}

// Green-dot API-health indicator + bring-your-own-key settings. The dot proves the
// user's own LLM is reachable (green) or that the app is grading deterministically
// offline (grey); a configured-but-unreachable provider shows red with the reason.
export default function LlmSettings() {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [cfg, setCfg] = useState<LlmConfig>(() => loadLlmConfig());
  const [providerId, setProviderId] = useState<string>(() =>
    providerIdFor(loadLlmConfig().baseUrl),
  );
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [checking, setChecking] = useState(true);
  const rootRef = useRef<HTMLDivElement>(null);

  const modelHint = PROVIDERS.find((p) => p.id === providerId)?.modelHint || "model-id";

  // Picking a provider prefills its base URL; "Custom" clears it for a manual endpoint.
  function pickProvider(id: string) {
    setProviderId(id);
    const p = PROVIDERS.find((x) => x.id === id);
    if (p && id !== "custom") setCfg((c) => ({ ...c, baseUrl: p.baseUrl }));
  }

  async function refresh() {
    setChecking(true);
    try {
      setStatus(await api.llmStatus());
    } catch {
      setStatus({ mode: "offline", online: false, configured: false });
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  // Click-away close (projector-safe: no hover).
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  async function save() {
    saveLlmConfig(cfg);
    await refresh();
  }

  const state = toState(status, checking);
  const label = checking
    ? t("llm.checking")
    : state === "online"
      ? t("llm.live")
      : state === "error"
        ? t("llm.unreachable")
        : t("llm.offline");

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="btn-ghost flex items-center gap-2 normal-case"
        aria-expanded={open}
        title={status?.model ? `${label} · ${status.model}` : label}
      >
        <span className={`h-2 w-2 rounded-full ${dotClass(state)}`} />
        {label}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-80 rounded-md border border-rule bg-ink-2 p-4 text-left shadow-xl">
          <h3 className="eyebrow mb-1">{t("llm.title")}</h3>
          <p className="mb-3 text-xs leading-relaxed text-muted">
            {t("llm.intro")}
          </p>

          <label className="eyebrow mb-1 block">{t("llm.provider")}</label>
          <select
            value={providerId}
            onChange={(e) => pickProvider(e.target.value)}
            className="well mb-3 w-full px-2 py-1.5 text-xs"
          >
            {PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>

          <label className="eyebrow mb-1 block">{t("llm.base_url")}</label>
          <input
            value={cfg.baseUrl}
            onChange={(e) => {
              const baseUrl = e.target.value;
              setCfg({ ...cfg, baseUrl });
              setProviderId(providerIdFor(baseUrl));
            }}
            placeholder="https://…/v1"
            className="well mb-3 w-full px-2 py-1.5 font-mono text-xs"
            autoComplete="off"
            spellCheck={false}
          />

          <label className="eyebrow mb-1 block">{t("llm.api_key")}</label>
          <input
            value={cfg.apiKey}
            onChange={(e) => setCfg({ ...cfg, apiKey: e.target.value })}
            type="password"
            placeholder="sk-…"
            className="well mb-3 w-full px-2 py-1.5 font-mono text-xs"
            autoComplete="off"
            spellCheck={false}
          />

          <label className="eyebrow mb-1 block">{t("llm.model")}</label>
          <input
            value={cfg.model}
            onChange={(e) => setCfg({ ...cfg, model: e.target.value })}
            placeholder={modelHint}
            className="well mb-3 w-full px-2 py-1.5 font-mono text-xs"
            autoComplete="off"
            spellCheck={false}
          />

          <button
            onClick={save}
            disabled={checking}
            className="btn-primary flex w-full items-center justify-center gap-2"
          >
            {checking && <Spinner />}
            {t("llm.save_test")}
          </button>

          <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed">
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${dotClass(state)}`} />
            <span className="text-muted">
              {state === "online"
                ? t("llm.status_online", { model: status?.model ?? "" })
                : state === "error"
                  ? t("llm.status_error", { error: status?.error ?? "" })
                  : t("llm.status_offline")}
            </span>
          </p>

          <p className="mt-3 border-t border-rule pt-2 text-[11px] leading-relaxed text-muted-2">
            {t("llm.privacy")}
          </p>
        </div>
      )}
    </div>
  );
}
