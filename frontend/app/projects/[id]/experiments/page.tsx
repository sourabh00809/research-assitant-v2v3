"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { api, postApi } from "../../../../lib/api";
import { Panel, EmptyState, LoadingSpinner } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

export default function ExperimentsPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, mutate, isLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const [busy, setBusy] = useState("");
  const [scriptId, setScriptId] = useState<string | null>(null);
  const [script, setScript] = useState("");
  const [error, setError] = useState("");

  const project = projects?.find((p) => p.id === projectId);
  const plans = project?.experiment_plans ?? [];

  async function recommendPlan() {
    setBusy("recommend");
    try {
      const plan = await postApi<any>(`/api/projects/${projectId}/experiment-plans/recommend`, {
        question: project?.briefs?.[0]?.title || "Research investigation",
        brief_id: project?.briefs?.[0]?.id || "",
      });
      await postApi<any>(`/api/projects/${projectId}/experiment-plans`, {
        objective: plan.objective || plan.task || "Experiment plan",
        domain: plan.domain || "ai",
        task: plan.task || "classification",
        hypothesis_id: "",
      });
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create experiment plan");
    }
    setBusy("");
  }

  async function generateScript(planId: string) {
    setBusy(`script-${planId}`);
    setScriptId(planId);
    setScript("");
    try {
      const res = await postApi<any>(`/api/projects/${projectId}/experiment-plans/${planId}/generate-script`, {});
      setScript(res.generated_script || "// No script generated");
    } catch { setScript("// Failed to generate script"); }
    setBusy("");
  }

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading experiment plans..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  if (isLoading) return <SidebarLayout><LoadingSpinner text="Loading experiment plans..." /></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Experiment Planner</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{project?.name} · {plans.length} experiment plans</p>
          </div>
          <button
            className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 disabled:opacity-50"
            disabled={busy === "recommend"}
            onClick={recommendPlan}
          >
            {busy === "recommend" ? "Generating..." : "Generate Plan"}
          </button>
        </header>

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300">{error}</div>
        )}

        {plans.length ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {plans.map((plan) => (
              <Panel key={plan.id} title={plan.title || plan.objective || "Experiment Plan"} meta={plan.status}>
                <div className="grid gap-3 text-sm">
                  {plan.objective && <p className="text-slate-600 dark:text-slate-300">{plan.objective}</p>}

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {(plan.datasets?.length ?? 0) > 0 && (
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">Datasets:</span>
                        <p className="text-slate-500 dark:text-slate-400">{plan.datasets!.join(", ")}</p>
                      </div>
                    )}
                    {(plan.baselines?.length ?? 0) > 0 && (
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">Baselines:</span>
                        <p className="text-slate-500 dark:text-slate-400">{plan.baselines!.join(", ")}</p>
                      </div>
                    )}
                    {(plan.metrics?.length ?? 0) > 0 && (
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">Metrics:</span>
                        <p className="text-slate-500 dark:text-slate-400">{plan.metrics!.join(", ")}</p>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-2 dark:border-slate-700">
                    <button
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700/50"
                      disabled={busy === `script-${plan.id}`}
                      onClick={() => generateScript(plan.id)}
                    >
                      {busy === `script-${plan.id}` ? "Generating..." : "Generate Script"}
                    </button>
                    <a
                      href={`/api/projects/${projectId}/experiment-plans/${plan.id}/export.md`}
                      target="_blank"
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700/50"
                    >
                      Export Markdown
                    </a>
                  </div>

                  {scriptId === plan.id && script && (
                    <div className="mt-2">
                      <details>
                        <summary className="cursor-pointer text-xs font-semibold text-emerald-600 dark:text-emerald-400">Show Generated Script</summary>
                        <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">{script}</pre>
                      </details>
                    </div>
                  )}
                </div>
              </Panel>
            ))}
          </div>
        ) : (
          <EmptyState text="Click 'Generate Plan' to create an experiment design pack based on your research brief." />
        )}
      </div>
    </SidebarLayout>
  );
}