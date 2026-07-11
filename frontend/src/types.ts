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
}

export interface Prompt {
  id: string;
  source: string;
  raw_text: string;
  tags: string[];
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
