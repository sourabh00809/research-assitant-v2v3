"use client";

import type { AdminHealth } from "../lib/api";
import { labelize } from "./ui";

export default function HealthCard({
  expanded,
  health,
  name,
  onToggle,
}: {
  expanded: boolean;
  health?: AdminHealth;
  name: string;
  onToggle: () => void;
}) {
  const value = health?.[name] as Record<string, unknown> | undefined;
  const status = String(value?.status ?? value?.backend ?? "unknown");
  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <button className="flex w-full items-center justify-between gap-3 text-left" onClick={onToggle}>
        <span>
          <span className="block text-sm font-bold">{labelize(name)}</span>
          <span className="text-xs text-slate-500">{status}</span>
        </span>
        <span className="text-xs font-semibold text-slate-500">{expanded ? "Hide" : "Details"}</span>
      </button>
      {expanded && (
        <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(value ?? {}, null, 2)}
        </pre>
      )}
    </article>
  );
}
