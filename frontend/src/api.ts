import type {
  Row,
  PromptDetailRow,
  AuditEntry,
  CalibrationRule,
  OverrideResult,
  Grade,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
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
    }),

  remediate: (id: string) =>
    request<Row>(`/remediate/${encodeURIComponent(id)}`, { method: "POST" }),

  override: (prompt_id: string, to_grade: Grade, reason: string) =>
    request<OverrideResult>("/override", {
      method: "POST",
      body: JSON.stringify({ prompt_id, to_grade, reason }),
    }),
};

export const AUDIT_CSV_URL = `${BASE}/audit/export.csv`;
