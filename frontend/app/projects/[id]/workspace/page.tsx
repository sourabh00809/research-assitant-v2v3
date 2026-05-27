"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { api, postApi } from "../../../../lib/api";
import { Panel, EmptyState, LoadingSpinner, MetricCard } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

const SOURCES = [
  { key: "arxiv", label: "arXiv" },
  { key: "semantic_scholar", label: "Semantic Scholar" },
  { key: "pubmed", label: "PubMed" },
  { key: "openalex", label: "OpenAlex" },
  { key: "core", label: "CORE" },
  { key: "crossref", label: "CrossRef" },
];

const PROVIDERS = [
  { key: "", label: "Auto" },
  { key: "openai", label: "OpenAI" },
  { key: "groq", label: "Groq" },
  { key: "huggingface", label: "HuggingFace" },
  { key: "ollama", label: "Ollama" },
];

type BriefResult = {
  error?: string;
  brief?: {
    title: string;
    evidence_items?: unknown[];
    question_interpretation?: string;
    key_findings?: string[];
    suggested_next_directions?: string[];
  };
};

export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, mutate } = useSWR<Project[]>("/api/v1/projects", api);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<BriefResult | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [provider, setProvider] = useState("");
  const [webSearch, setWebSearch] = useState(false);

  const project = projects?.find((p) => p.id === projectId);
  const brief = project?.briefs?.[0];
  const evidence = brief?.evidence_items ?? [];

  function toggleSource(key: string) {
    setSelectedSources((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }

  async function runQuestion() {
    if (!question.trim()) return;
    setBusy("run");
    setResult(null);
    try {
      const body: Record<string, unknown> = { question, max_papers: 6, use_memory: true };
      if (selectedSources.length > 0) body.sources = selectedSources;
      if (provider) body.provider = provider;
      if (webSearch) body.web_search = true;
      const res = await postApi<BriefResult>(`/api/projects/${projectId}/questions/run`, body);
      setResult(res);
      await mutate();
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : "Run failed" });
    }
    setBusy("");
  }

  if (!isLoaded) return <LoadingSpinner text="Loading..." />;
  if (!isSignedIn) { router.replace("/sign-in"); return null; }

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
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    {showAdvanced ? "Hide" : "Show"} Advanced
                  </button>
                </div>

                {showAdvanced && (
                  <div className="mt-2 grid gap-4 rounded-md border border-slate-200 bg-slate-50 p-4">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Paper Sources</span>
                      <p className="mb-2 text-xs text-slate-400">Leave all unchecked to use all available sources.</p>
                      <div className="flex flex-wrap gap-3">
                        {SOURCES.map((s) => (
                          <label key={s.key} className="flex items-center gap-1.5 text-sm text-slate-700">
                            <input
                              type="checkbox"
                              checked={selectedSources.includes(s.key)}
                              onChange={() => toggleSource(s.key)}
                              className="rounded border-slate-300 text-emerald-700 focus:ring-emerald-500"
                            />
                            {s.label}
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-6">
                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">AI Provider</span>
                        <select
                          value={provider}
                          onChange={(e) => setProvider(e.target.value)}
                          className="mt-1 rounded-md border border-slate-300 p-2 text-sm"
                        >
                          {PROVIDERS.map((p) => (
                            <option key={p.key} value={p.key}>{p.label}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Web Search</span>
                        <label className="mt-1 flex items-center gap-1.5 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={webSearch}
                            onChange={(e) => setWebSearch(e.target.checked)}
                            className="rounded border-slate-300 text-emerald-700 focus:ring-emerald-500"
                          />
                          Enable Tavily web search
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Panel>

            {result?.error ? (
              <Panel title="Error">
                <p className="text-sm text-red-600">{String(result.error)}</p>
              </Panel>
            ) : null}

            {result?.brief ? (
              <Panel title={result.brief.title} meta={`${result.brief.evidence_items?.length ?? 0} evidence items`}>
                <div className="grid gap-4">
                  {result.brief.question_interpretation ? (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Interpretation</h3>
                      <p className="text-sm text-slate-700">{result.brief.question_interpretation}</p>
                    </div>
                  ) : null}

                  {result.brief.key_findings?.length ? (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Key Findings</h3>
                      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                        {result.brief.key_findings.slice(0, 5).map((f: string, i: number) => <li key={i}>{f}</li>)}
                      </ul>
                    </div>
                  ) : null}

                  {result.brief.suggested_next_directions?.length ? (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Next Directions</h3>
                      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                        {result.brief.suggested_next_directions.slice(0, 3).map((d: string, i: number) => <li key={i}>{d}</li>)}
                      </ul>
                    </div>
                  ) : null}

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
            ) : null}

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
                    <li>Search relevant literature from arXiv, Semantic Scholar, OpenAlex, CORE, CrossRef, and PubMed</li>
                    <li>Extract claims, methods, datasets, and limitations</li>
                    <li>Compare papers in a structured methodology matrix</li>
                    <li>Generate a grounded research brief with citations</li>
                    <li>Suggest experiment plans, hypotheses, and next directions</li>
                  </ol>
                  <p className="mt-2 text-xs text-slate-400">Click <strong>Show Advanced</strong> to select specific sources, AI provider, or enable web search.</p>
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