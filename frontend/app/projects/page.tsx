"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { api, postApi } from "../../lib/api";
import { Panel, EmptyState, LoadingSpinner, MetricCard } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";

export default function ProjectsPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const { data: projects, error, mutate, isLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const [busy, setBusy] = useState(false);
  const [createError, setCreateError] = useState("");

  async function createProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    if (!name) return;
    setBusy(true);
    try {
      const project = await postApi<Project>("/api/v1/projects", { name, description: "Research workspace" });
      await mutate();
      router.push(`/projects/${project.id}/workspace`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create project");
    }
    setBusy(false);
  }

  if (!isLoaded) return <LoadingSpinner text="Loading..." />;
  if (!isSignedIn) { router.replace("/login"); return null; }

  const totalBriefs = projects?.reduce((s, p) => s + (p.briefs?.length ?? 0), 0) ?? 0;
  const totalPlans = projects?.reduce((s, p) => s + (p.experiment_plans?.length ?? 0), 0) ?? 0;
  const totalAgents = projects?.reduce((s, p) => s + ((p as any).autonomous_agents?.length ?? 0), 0) ?? 0;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Research Projects</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Manage your research investigations and experiments.</p>
          </div>
        </header>

        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          <MetricCard title="Projects" value={projects?.length ?? 0} detail="active workspaces" />
          <MetricCard title="Research Briefs" value={totalBriefs} detail="generated syntheses" />
          <MetricCard title="Experiment Plans" value={totalPlans} detail="design packs" />
          <MetricCard title="Research Agents" value={totalAgents} detail="supervised workflows" />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <Panel title="All Projects" meta={`${projects?.length ?? 0} total`}>
            {isLoading ? <LoadingSpinner text="Loading projects..." /> : error ? (
              <p className="text-sm text-red-600 dark:text-red-400">Failed to load projects.</p>
            ) : projects?.length ? (
              <div className="grid gap-3">
                {projects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => router.push(`/projects/${project.id}/workspace`)}
                    className="w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition-all hover:border-emerald-300 hover:shadow-sm dark:border-slate-600 dark:bg-slate-800 dark:hover:border-emerald-600"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100">{project.name}</h3>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 line-clamp-2">{project.description || "No description"}</p>
                      </div>
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400 dark:text-slate-500">
                      <span>{project.briefs?.length ?? 0} briefs</span>
                      <span className="text-slate-300 dark:text-slate-500">|</span>
                      <span>{project.experiment_plans?.length ?? 0} plans</span>
                      <span className="text-slate-300 dark:text-slate-500">|</span>
                      <span>{project.memory?.length ?? 0} memory items</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : <EmptyState text="Create your first research project to get started." />}
          </Panel>

          <Panel title="New Project">
            {createError && (
              <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300">{createError}</div>
            )}
            <form className="grid gap-4" onSubmit={createProject}>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">Project Name</label>
                <input className="w-full rounded-md border border-slate-300 p-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-emerald-400" name="name" placeholder="e.g., Literature Review on RAG" required />
              </div>
              <button
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 disabled:opacity-50"
                disabled={busy}
              >
                {busy ? "Creating..." : "Create Project"}
              </button>
            </form>
          </Panel>
        </div>
      </div>
    </SidebarLayout>
  );
}