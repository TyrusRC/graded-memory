export type Grade = "KEEP" | "REVISE" | "RETIRE";

export interface RiskHit {
  category: string;
  match: string;
  severity: string;
  detail: string;
}

export interface Rubric {
  clarity: number;
  context: number;
  output_quality: number;
  safety: number;
}

export interface Grading {
  prompt_id: string;
  grade: Grade;
  rubric: Rubric;
  rationale: string;
  risks_found: RiskHit[];
  control_map: string[];
  model: string;
  // The action chain the agentic Judge foresaw an agent taking; [] offline/passive.
  foreseen_actions: string[];
}

export interface LlmStatus {
  mode: "live" | "offline";
  online: boolean;
  configured: boolean;
  model?: string;
  error?: string;
}

export type Kind = "prompt" | "workflow" | "agent";

export interface Prompt {
  id: string;
  source: string;
  raw_text: string;
  tags: string[];
  kind: Kind;
  context: string;
}

export interface ReuseMatch {
  prompt: Prompt;
  grading: Grading | null;
  score: number;
}

export interface Analytics {
  by_kind: Record<string, number>;
  by_tag: {
    tag: string;
    count: number;
    keep: number;
    revise: number;
    retire: number;
  }[];
  duplicates: {
    members: { prompt_id: string; source: string }[];
    score: number;
  }[];
  growth: { date: string; graded_count: number }[];
  coverage_gaps: string[];
}

export interface Row {
  prompt: Prompt;
  grading: Grading | null;
}

export interface AuditEntry {
  id: number;
  prompt_id: string;
  action: string;
  grade: Grade | null;
  detail: string;
  ts: string;
}

export interface PromptDetailRow extends Row {
  audit: AuditEntry[];
}

export interface CalibrationRule {
  id: number;
  pattern: string;
  rule: string;
  ts: string;
}

export interface OverrideResult {
  changed: string[];
  count: number;
}
