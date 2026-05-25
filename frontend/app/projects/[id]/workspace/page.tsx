"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { api, postApi } from "../../../../lib/api";
import { useSession } from "../../../../components/AuthProvider";
import { Panel, EmptyState, LoadingSpinner, MetricCard } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

const SUGGESTED_QUERIES = [
  "Retrieval-Augmented Generation for knowledge-intensive tasks",
  "Multi-agent systems for scientific discovery",
  "Evaluation of large language model reasoning capabilities",
];

export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const { session } = useSession();
  const projectId = params.id as string;
  const { data: projects, mutate } = useSWR<Project[]>("/api/v1/projects", api);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const project = projects?.find((p) => p.id === projectId);
  const brief = project?.briefs?.[0];
  const evidence = brief?.evidence_items ?? [];

  async function runQuestion() {
    if (!question.trim()) return;
    setBusy("run");
    setResult(null);
    try {
      const res = await postApi<any>(`/api/projects/${projectId}/questions/run`, { question, max_papers: 6, use_memory: true });
      setResult(res);
      await mutate();
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : "Run failed" });
    }
    setBusy("");
  }

  if (!session?.authenticated) { router.replace("/login"); return null; }

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">{project?.name ?? "Workspace"}</h1>
          <p className="mt-1 text-sm text-slate-500">{project?.description ?? "Research investigation workspace"}</p>
        </header>

        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          <MetricCard title="Research Briefs" value={project?.briefs?.length ?? 0} detail="generated syntheses" />
          <MetricCard title="Evidence Items" value={evidence.length} detail="citation-grounded claims" />
          <MetricCard title="Experiment Plans" value={project?.experiment_plans?.length ?? 0} detail="design packs" />
          <MetricCard title="Hypotheses" value={(project as any)?.hypotheses?.length ?? 0} detail="generated candidates" />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
          <div className="grid gap-6">
            <Panel title="Research Question">
              <div className="grid gap-3">
                <textarea
                  className="w-full rounded-md border border-slate-300 p-3 text-sm focus:border-emerald-500 focus:outline-none"
                  rows={3}
                  placeholder="Enter a research question..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
                    disabled={busy === "run" || !question.trim()}
                    onClick={runQuestion}
                  >
                    {busy === "run" ? "Investigating..." : "Run Investigation"}
                  </button>
                  <button
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    onClick={() => {
                      const next = SUGGESTED_QUERIES[Math.floor(Math.random() * SUGGESTED_QUERIES.length)];
                      setQuestion(next);
                    }}
                  >
                    Suggest Query
                  </button>
                </div>
              </div>
            </Panel>

            {result?.error && (
              <Panel title="Error">
                <p className="text-sm text-red-600">{result.error}</p>
              </Panel>
            )}

            {result?.brief && (
              <Panel title={result.brief.title} meta={`${result.brief.evidence_items?.length ?? 0} evidence items`}>
                <div className="grid gap-4">
                  {result.brief.question_interpretation && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Interpretation</h3>
                      <p className="text-sm text-slate-700">{result.brief.question_interpretation}</p>
                    </div>
                  )}

                  {result.brief.key_findings?.length > 0 && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Key Findings</h3>
                      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                        {result.brief.key_findings.slice(0, 5).map((f: string, i: number) => <li key={i}>{f}</li>)}
                      </ul>
                    </div>
                  )}

                  {result.brief.suggested_next_directions?.length > 0 && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Next Directions</h3>
                      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                        {result.brief.suggested_next_directions.slice(0, 3).map((d: string, i: number) => <li key={i}>{d}</li>)}
                      </ul>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-3">
                    <button onClick={() => router.push(`/projects/${projectId}/evidence`)} className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                      View All Evidence
                    </button>
                    <button onClick={() => router.push(`/projects/${projectId}/experiments`)} className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                      Create Experiment Plan
                    </button>
                    <button onClick={() => router.push(`/projects/${projectId}/graph`)} className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                      View Research Graph
                    </button>
                  </div>
                </div>
              </Panel>
            )}

            {evidence.length > 0 && !result && (
              <Panel title="Latest Evidence" meta={`${evidence.length} items`}>
                <div className="grid gap-3 md:grid-cols-2">
                  {evidence.slice(0, 6).map((item) => (
                    <article key={item.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-bold uppercase text-emerald-800">
                          {item.extraction_type}
                        </span>
                        <span className="truncate text-xs text-slate-400">{item.source_id}</span>
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{item.claim}</p>
                    </article>
                  ))}
                </div>
                {evidence.length > 6 && (
                  <button onClick={() => router.push(`/projects/${projectId}/evidence`)} className="mt-3 text-xs font-semibold text-emerald-600 hover:text-emerald-700">
                    View all {evidence.length} items →
                  </button>
                )}
              </Panel>
            )}

            {!evidence.length && !result && (
              <Panel title="Getting Started">
                <div className="grid gap-3 text-sm text-slate-600">
                  <p>Enter a research question above and click <strong>Run Investigation</strong> to generate a citation-grounded research brief.</p>
                  <p>The system will:</p>
                  <ol className="list-inside list-decimal space-y-1">
                    <li>Search relevant literature from arXiv and Semantic Scholar</li>
                    <li>Extract claims, methods, datasets, and limitations</li>
                    <li>Compare papers in a structured methodology matrix</li>
                    <li>Generate a grounded research brief with citations</li>
                    <li>Suggest experiment plans, hypotheses, and next directions</li>
                  </ol>
                </div>
              </Panel>
            )}
          </div>

          <div className="grid gap-6">
            <Panel title="Quick Actions">
              <div className="grid gap-2">
                <button onClick={() => router.push(`/projects/${projectId}/evidence`)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Browse Evidence
                </button>
                <button onClick={() => router.push(`/projects/${projectId}/experiments`)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Experiment Planner
                </button>
                <button onClick={() => router.push(`/projects/${projectId}/memory`)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Research Memory
                </button>
                <button onClick={() => router.push(`/projects/${projectId}/papers`)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Source Library
                </button>
                <button onClick={() => router.push(`/projects/${projectId}/graph`)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Research Graph
                </button>
              </div>
            </Panel>

            <Panel title="Project Info" meta={project?.id ? "active" : "loading"}>
              {project ? (
                <div className="grid gap-2 text-xs text-slate-500">
                  <p><span className="font-semibold text-slate-700">ID:</span> {project.id}</p>
                  <p><span className="font-semibold text-slate-700">Briefs:</span> {project.briefs?.length ?? 0}</p>
                  <p><span className="font-semibold text-slate-700">Plans:</span> {project.experiment_plans?.length ?? 0}</p>
                  <p><span className="font-semibold text-slate-700">Memory:</span> {project.memory?.length ?? 0} items</p>
                </div>
              ) : <LoadingSpinner text="Loading project..." />}
            </Panel>
          </div>
        </div>
      </div>
    </SidebarLayout>
  );
}