import { useState } from "react";
import type { Grade } from "../types";

const gradeStamp: Record<Grade, string> = {
  KEEP: "stamp-keep",
  REVISE: "stamp-revise",
  RETIRE: "stamp-retire",
};

export function GradeBadge({
  grade,
  size = "sm",
}: {
  grade: Grade | null;
  size?: "sm" | "lg";
}) {
  const label = grade ?? "UNGRADED";
  const tone = grade ? gradeStamp[grade] : "stamp-ungraded";
  const dims = size === "lg" ? "stamp-lg" : "stamp-sm";
  return <span className={`stamp ${dims} ${tone}`}>{label}</span>;
}

function severityChip(severity: string): string {
  switch (severity.toLowerCase()) {
    case "high":
      return "chip-high";
    case "medium":
      return "chip-medium";
    default:
      return "chip-low";
  }
}

export function RiskChip({
  category,
  severity,
}: {
  category: string;
  severity: string;
}) {
  return (
    <span className={`chip ${severityChip(severity)}`} title={severity}>
      {category}
    </span>
  );
}

export function Tag({ children }: { children: React.ReactNode }) {
  return <span className="tag">{children}</span>;
}

const STATUS_META = {
  built: { label: "BUILT", tone: "text-keep" },
  planned: { label: "PLANNED", tone: "text-muted" },
  concept: { label: "DEMONSTRATED CONCEPT", tone: "text-revise" },
} as const;

// Candor as a product property: label what is real vs. planned, honestly.
export function StatusChip({ status }: { status: keyof typeof STATUS_META }) {
  const s = STATUS_META[status];
  return <span className={`tag ${s.tone}`}>{s.label}</span>;
}

// Single newcomer aid: click-to-reveal glossary (no hover — projector-safe).
export function Term({
  term,
  children,
}: {
  term: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="cursor-help border-b border-dotted border-muted-2 text-inherit"
      >
        {term}
      </button>
      {open && (
        <span className="absolute left-0 top-full z-20 mt-1 block w-64 rounded-md border border-rule bg-ink-2 p-2 text-left text-xs font-normal leading-relaxed tracking-normal text-muted normal-case shadow-lg">
          {children}
        </span>
      )}
    </span>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      width="16"
      height="16"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-90"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
      />
    </svg>
  );
}
