"use client";

import type { AgentRun } from "../lib/api";
import { StatusBadge } from "./ui";

export default function AgentRunCard({
  busyAction,
  onApprove,
  onAudit,
  run,
}: {
  busyAction: string;
  onApprove: () => void;
  onAudit: () => void;
  run: AgentRun;
}) {
  const pending = run.decisions?.some((d) => d.requires_approval && !d.approved);
  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-600 dark:bg-slate-800/50">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge value={run.status} />
        <span className="text-xs text-slate-500 dark:text-slate-400">{run.decisions?.length ?? 0} decisions</span>
      </div>
      <p className="mt-2 text-sm font-semibold dark:text-slate-100">{run.current_step || "queued"}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200" onClick={onAudit}>
          {busyAction === `audit-${run.id}` ? "Loading..." : "Audit"}
        </button>
        {pending && (
          <button
            className="rounded-md bg-emerald-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50 dark:bg-emerald-600"
            disabled={busyAction === `approve-${run.id}`}
            onClick={onApprove}
          >
            {busyAction === `approve-${run.id}` ? "Approving..." : "Approve"}
          </button>
        )}
      </div>
    </article>
  );
}
