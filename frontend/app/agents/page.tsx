"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project, AgentAudit, AgentRun } from "../../lib/api";
import { api, postApi } from "../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { Panel, EmptyState, LoadingSpinner } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";
import AgentRunCard from "../../components/AgentRunCard";

export default function AgentsPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const { data: projects, mutate: refreshProjects, isLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");
  const [audit, setAudit] = useState<AgentAudit | null>(null);

  const active = projects?.[0];
  const agentRuns = active?.autonomous_agent_runs ?? [];
  const pendingRun = agentRuns.find((r) => r.decisions?.some((d) => d.requires_approval && !d.approved));
  const runnableRun = pendingRun ?? agentRuns[0];

  async function withAction(label: string, work: () => Promise<void>) {
    setBusyAction(label); setMessage("");
    try { await work(); } catch { setMessage("Action failed."); }
    setBusyAction("");
  }

  async function createAgent(type: string) {
    if (!active) return;
    await withAction(type, async () => {
      await postApi(`/api/v1/projects/${active.id}/agents`, {
        type, name: type.replace("_", " "),
        goal: "Prepare approved research workflow", schedule: "weekly",
      });
      await refreshProjects();
    });
  }

  async function runAgentStep() {
    if (!active || !runnableRun) return;
    await withAction("step", async () => {
      await postApi(`/api/v1/agent-runs/${runnableRun.id}/step?project_id=${active.id}`, {});
      await refreshProjects();
    });
  }

  async function approveRun(run: AgentRun) {
    if (!active) return;
    await withAction(`approve-${run.id}`, async () => {
      await postApi(`/api/v1/agent-runs/${run.id}/approve?project_id=${active.id}`, {});
      await refreshProjects();
    });
  }

  async function loadAudit(run: AgentRun) {
    if (!active) return;
    await withAction(`audit-${run.id}`, async () => {
      setAudit(await api<AgentAudit>(`/api/v1/agent-runs/${run.id}/audit?project_id=${active.id}`));
    });
  }

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading agents..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  if (isLoading) return <SidebarLayout><LoadingSpinner text="Loading agents..." /></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold dark:text-slate-100">Agent Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Manage autonomous research agents and approvals.</p>

        {message && (
          <div className="mt-4 rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300">{message}</div>
        )}

        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Panel title="Agent Controls" meta={`${agentRuns.length} runs`}>
            <div className="mb-4 flex flex-wrap gap-2">
              <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                disabled={!active || busyAction === "literature_monitor"}
                onClick={() => createAgent("literature_monitor")}>Create Monitor</button>
              <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                disabled={!active || busyAction === "experiment_runner"}
                onClick={() => createAgent("experiment_runner")}>Create Runner</button>
              <button className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-emerald-600 dark:hover:bg-emerald-500"
                disabled={!runnableRun || busyAction === "step"} onClick={runAgentStep}>
                {busyAction === "step" ? "Running..." : "Run Step"}
              </button>
            </div>

            {agentRuns.length ? (
              <div className="grid gap-3">
                {agentRuns.map((run) => (
                  <AgentRunCard key={run.id} run={run} busyAction={busyAction}
                    onApprove={() => approveRun(run)} onAudit={() => loadAudit(run)} />
                ))}
              </div>
            ) : <EmptyState text="Create a monitor or runner to start." />}
          </Panel>

          <Panel title="Audit Log" meta={audit ? "loaded" : "empty"}>
            {audit ? (
              <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(audit, null, 2)}
              </pre>
            ) : <EmptyState text="Click Audit on an agent run to view decision history." />}
          </Panel>

          <Panel title="Artifacts" meta={`${active?.execution_artifacts?.length ?? 0} total`} className="lg:col-span-2">
            {active?.execution_artifacts?.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {active.execution_artifacts.map((a) => (
                  <article key={a.id} className="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-600 dark:bg-slate-800/50">
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold uppercase text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">{a.kind}</span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">{a.run_id}</span>
                    </div>
                    <p className="mt-2 line-clamp-3 text-sm text-slate-700 dark:text-slate-200">{a.content || a.path || "Stored artifact"}</p>
                  </article>
                ))}
              </div>
            ) : <EmptyState text="Sandbox runs generate artifacts here." />}
          </Panel>
        </div>
      </div>
    </SidebarLayout>
  );
}
