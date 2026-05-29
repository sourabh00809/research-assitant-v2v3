"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project, AdminHealth } from "../../lib/api";
import { useUser, useAuth } from "@clerk/nextjs";
import { api, postApi } from "../../lib/api";
import { MetricCard, Panel, EmptyState, LoadingSpinner, ErrorBanner } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";
import HealthCard from "../../components/HealthCard";

const DEFAULT_QUERY = "retrieval augmented research agents";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useUser();
  const { isLoaded, isSignedIn } = useAuth();
  const { data: projects, error: projectsError, mutate: refreshProjects, isLoading: projectsLoading } = useSWR<Project[]>(
    "/api/v1/projects", api
  );
  const { data: health, isLoading: healthLoading } = useSWR<AdminHealth>("/api/v1/admin/health", api);

  const [activeProjectId, setActiveProjectId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [expandedHealth, setExpandedHealth] = useState("");

  const active = projects?.find((p) => p.id === activeProjectId) ?? projects?.[0];
  const activeBrief = active?.briefs?.[0];
  const evidence = activeBrief?.evidence_items ?? [];

  async function withAction(label: string, work: () => Promise<void>) {
    setBusyAction(label);
    setErrorMessage("");
    setMessage("");
    try {
      await work();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusyAction("");
    }
  }

  async function createProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("project_name") ?? "").trim();
    if (!name) return;
    await withAction("project", async () => {
      const project = await postApi<Project>("/api/v1/projects", { name, description: "Research workspace" });
      setActiveProjectId(project.id);
      await refreshProjects();
      setMessage(`Created: ${project.name}`);
      (event.target as HTMLFormElement).reset();
    });
  }

  async function runQuestion() {
    if (!active) return;
    await withAction("question", async () => {
      await postApi(`/api/projects/${active.id}/questions/run`, { question: DEFAULT_QUERY });
      await refreshProjects();
      setMessage("Research question submitted.");
    });
  }

  if (!isLoaded) return <LoadingSpinner text="Loading..." />;
  if (!isSignedIn) {
    router.replace("/login");
    return null;
  }

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-300 pb-5 dark:border-slate-600">
          <div>
            <h1 className="text-3xl font-bold">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {user?.primaryEmailAddress?.emailAddress ?? "Researcher"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-md bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
              disabled={busyAction === "question" || !active}
              onClick={runQuestion}
            >
              {busyAction === "question" ? "Running..." : "Run Question"}
            </button>
            <a
              href="/sign-out"
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              Logout
            </a>
            <a className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" href="/legacy">
              Legacy UI
            </a>
          </div>
        </header>

        {(errorMessage || message) && (
          <div className={`mt-4 rounded-md border p-3 text-sm font-semibold ${
            errorMessage ? "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300" : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
          }`}>
            {errorMessage || message}
          </div>
        )}

        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCard title="Projects" value={projects?.length ?? 0} detail="available workspaces" />
          <MetricCard title="Briefs" value={active?.briefs?.length ?? 0} detail="generated syntheses" />
          <MetricCard title="Evidence" value={evidence.length} detail="claims in latest brief" />
          <MetricCard title="Plans" value={active?.experiment_plans?.length ?? 0} detail="experiment packs" />
          <MetricCard title="Agents" value={active?.autonomous_agents?.length ?? 0} detail="supervised workflows" />
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 grid gap-6">
            <Panel title="Projects" meta={`${projects?.length ?? 0} total`}>
              {projectsLoading ? <LoadingSpinner text="Loading projects..." /> : projects?.length ? (
                <div className="grid gap-3">
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      className={`w-full rounded-md border p-4 text-left transition-colors ${
                        active?.id === project.id ? "border-emerald-500 bg-emerald-50 dark:border-emerald-600 dark:bg-emerald-900/30" : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700/50"
                      }`}
                      onClick={() => setActiveProjectId(project.id)}
                    >
                      <h3 className="font-bold">{project.name}</h3>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300 line-clamp-2">{project.description}</p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span>{project.briefs?.length ?? 0} briefs</span>
                        <span>{project.experiment_plans?.length ?? 0} plans</span>
                        <span>{project.memory?.length ?? 0} memory items</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : <EmptyState text="Create a project to get started." />}
            </Panel>

            <Panel title="Evidence" meta={active?.name ?? "No active project"}>
              {evidence.length ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {evidence.slice(0, 8).map((item) => (
                    <article key={item.id} className="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-600 dark:bg-slate-800/50">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold uppercase text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                          {item.extraction_type}
                        </span>
                        <span className="max-w-[12rem] truncate text-xs text-slate-500 dark:text-slate-400">{item.source_id}</span>
                      </div>
                      <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-800 dark:text-slate-200">{item.claim}</p>
                    </article>
                  ))}
                </div>
              ) : <EmptyState text="Run a research question to populate citation-grounded evidence." />}
            </Panel>

            <Panel title="Experiment Plans" meta={`${active?.experiment_plans?.length ?? 0} total`}>
              {active?.experiment_plans?.length ? (
                <div className="grid gap-3">
                  {active.experiment_plans.slice(0, 5).map((plan) => (
                    <article key={plan.id} className="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-600 dark:bg-slate-800/50">
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="text-sm font-bold">{plan.title}</h3>
                        <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold uppercase text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                          {plan.status}
                        </span>
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm text-slate-700 dark:text-slate-200">{plan.objective}</p>
                      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                        {(plan.datasets?.length ?? 0)} datasets / {(plan.baselines?.length ?? 0)} baselines / {(plan.metrics?.length ?? 0)} metrics
                      </p>
                    </article>
                  ))}
                </div>
              ) : <EmptyState text="Generate experiment plans from a research brief." />}
            </Panel>
          </div>

          <aside className="grid gap-6">
            <Panel title="Create Project" meta="quick start">
              <form className="grid gap-3" onSubmit={createProject}>
                <input className="rounded-md border border-slate-300 p-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" name="project_name" placeholder="Project name" />
                <button
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  disabled={busyAction === "project"}
                >
                  {busyAction === "project" ? "Creating..." : "Create"}
                </button>
              </form>
            </Panel>

            <Panel title="Platform Health" meta={healthLoading ? "checking" : "online"}>
              <div className="grid gap-3">
                {["database", "redis_workers", "storage", "sandbox"].map((key) => (
                  <HealthCard
                    key={key}
                    name={key}
                    health={health}
                    expanded={expandedHealth === key}
                    onToggle={() => setExpandedHealth(expandedHealth === key ? "" : key)}
                  />
                ))}
              </div>
            </Panel>
          </aside>
        </section>
      </div>
    </SidebarLayout>
  );
}
