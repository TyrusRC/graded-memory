import type {
  Row,
  PromptDetailRow,
  AuditEntry,
  CalibrationRule,
  OverrideResult,
  Grade,
  LlmStatus,
} from "./types";
import { llmHeaders } from "./llm";

// Relative in dev (Vite proxies /api → :8000); absolute in the hosted build,
// where the frontend (Firebase) calls the backend (Render) cross-origin.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

// `llm: true` attaches the browser's bring-your-own-key headers so the backend can
// grade live with the user's own provider; omit for read-only endpoints.
async function request<T>(
  path: string,
  init?: RequestInit & { llm?: boolean },
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.body ? { "Content-Type": "application/json" } : {}),
    ...(init?.llm ? llmHeaders() : {}),
  };
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `${init?.method ?? "GET"} ${path} failed: ${res.status} ${text}`.trim(),
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  library: () => request<Row[]>("/library"),

  newhire: () => request<Row[]>("/newhire"),

  prompt: (id: string) =>
    request<PromptDetailRow>(`/prompt/${encodeURIComponent(id)}`),

  audit: () => request<AuditEntry[]>("/audit"),

  calibration: () => request<CalibrationRule[]>("/calibration"),

  grade: (text: string) =>
    request<Row>("/grade", {
      method: "POST",
      body: JSON.stringify({ text }),
      llm: true,
    }),

  remediate: (id: string) =>
    request<Row>(`/remediate/${encodeURIComponent(id)}`, {
      method: "POST",
      llm: true,
    }),

  // Green-dot health probe: reports whether the configured provider actually answers.
  llmStatus: () => request<LlmStatus>("/llm/status", { llm: true }),

  override: (prompt_id: string, to_grade: Grade, reason: string) =>
    request<OverrideResult>("/override", {
      method: "POST",
      body: JSON.stringify({ prompt_id, to_grade, reason }),
    }),
};

export const AUDIT_CSV_URL = `${BASE}/audit/export.csv`;
