"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { api } from "../../../../lib/api";
import { Panel, EmptyState, LoadingSpinner, StatusBadge } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

export default function EvidencePage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, isLoading } = useSWR<Project[]>("/api/v1/projects", api);

  const project = projects?.find((p) => p.id === projectId);
  const allEvidence = project?.briefs?.flatMap((b) => b.evidence_items) ?? [];
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const types = [...new Set(allEvidence.map((e) => e.extraction_type))];
  const filtered = allEvidence.filter((e) => {
    if (filter !== "all" && e.extraction_type !== filter) return false;
    if (search && !e.claim.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading evidence..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  if (isLoading) return <SidebarLayout><LoadingSpinner text="Loading evidence..." /></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Evidence Inspector</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{project?.name} · {allEvidence.length} total evidence items</p>
        </header>

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input
            className="w-64 rounded-md border border-slate-300 p-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-emerald-400"
            placeholder="Search evidence..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <select
            className="rounded-md border border-slate-300 p-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            {types.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
          </select>

          <span className="text-xs text-slate-400 dark:text-slate-500">{filtered.length} of {allEvidence.length} shown</span>
        </div>

        {filtered.length ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((item) => (
              <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-600 dark:bg-slate-800">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <StatusBadge value={item.extraction_type} />
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {item.confidence} · {item.retrieval_method}
                  </span>
                </div>
                <p className="mb-3 text-sm leading-6 text-slate-800 dark:text-slate-200">{item.claim}</p>
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2 text-xs text-slate-400 dark:border-slate-700 dark:text-slate-500">
                  <span className="truncate max-w-[200px]" title={item.source_id}>{item.source_id}</span>
                  {item.semantic_score != null && <span>semantic: {item.semantic_score.toFixed(2)}</span>}
                </div>
                {item.source_quote && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-semibold text-emerald-600 dark:text-emerald-400">Source Quote</summary>
                    <p className="mt-1 rounded-md bg-slate-50 p-2 text-xs text-slate-600 italic dark:bg-slate-800/50 dark:text-slate-300">{item.source_quote}</p>
                  </details>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState text={search || filter !== "all" ? "No evidence matches your filters." : "Run a research question to populate evidence."} />
        )}
      </div>
    </SidebarLayout>
  );
}