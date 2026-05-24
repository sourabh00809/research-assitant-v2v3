"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import useSWR from "swr";
import {
  AdminHealth,
  AgentAudit,
  AgentRun,
  CheckoutResponse,
  EvidenceItem,
  Project,
  Session,
  api,
  postApi,
} from "../lib/api";

const DEFAULT_QUERY = "retrieval augmented research agents";

export default function Dashboard() {
  const { data: session, error: sessionError, mutate: refreshSession, isLoading: sessionLoading } = useSWR<Session>(
    "/api/v1/auth/session",
    api,
  );
  const { data: projects, error: projectsError, mutate: refreshProjects, isLoading: projectsLoading } = useSWR<Project[]>(
    "/api/v1/projects",
    api,
  );
  const { data: health, error: healthError, isLoading: healthLoading } = useSWR<AdminHealth>("/api/v1/admin/health", api);

  const [activeProjectId, setActiveProjectId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [busyAction, setBusyAction] = useState<string>("");
  const [expandedHealth, setExpandedHealth] = useState<string>("");
  const [audit, setAudit] = useState<AgentAudit | null>(null);

  const active = useMemo(() => {
    if (!projects?.length) return undefined;
    return projects.find((project) => project.id === activeProjectId) ?? projects[0];
  }, [activeProjectId, projects]);

  useEffect(() => {
    if (!activeProjectId && projects?.length) {
      setActiveProjectId(projects[0].id);
    }
  }, [activeProjectId, projects]);

  const activeBrief = active?.briefs?.[0];
  const evidence = activeBrief?.evidence_items ?? [];
  const agentRuns = active?.autonomous_agent_runs ?? [];
  const pendingRun = agentRuns.find((run) => run.decisions?.some((decision) => decision.requires_approval && !decision.approved));
  const runnableRun = pendingRun ?? agentRuns[0];

  async function withAction(label: string, work: () => Promise<void>) {
    setBusyAction(label);
    setErrorMessage("");
    setMessage("");
    try {
      await work();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setBusyAction("");
    }
  }

  async function signup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      email: String(form.get("email") ?? ""),
      password: String(form.get("password") ?? ""),
      team_name: String(form.get("team_name") ?? ""),
    };
    await withAction("auth", async () => {
      try {
        await postApi("/api/v1/auth/signup", payload);
        setMessage("Signed in and workspace session refreshed.");
      } catch (error) {
        await postApi("/api/v1/auth/login", { email: payload.email, password: payload.password });
        setMessage("Existing user signed in and session refreshed.");
      }
      await refreshSession();
    });
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("project_name") ?? "").trim();
    if (!name) return;
    await withAction("project", async () => {
      const project = await postApi<Project>("/api/v1/projects", {
        name,
        description: "V2/V3 beta smoke workspace.",
      });
      setActiveProjectId(project.id);
      await refreshProjects();
      setMessage(`Project created: ${project.name}`);
      event.currentTarget.reset();
    });
  }

  async function createAgent(type: string) {
    if (!active) return;
    await withAction(type, async () => {
      await postApi(`/api/v1/projects/${active.id}/agents`, {
        type,
        name: type.replace("_", " "),
        goal: type === "literature_monitor" ? "Find new research agent papers" : "Prepare approved research workflow",
        schedule: "weekly",
      });
      await refreshProjects();
      setMessage(`${labelize(type)} agent created.`);
    });
  }

  async function runAgentStep() {
    if (!active || !runnableRun) return;
    await withAction("run-step", async () => {
      await postApi(`/api/v1/agent-runs/${runnableRun.id}/step?project_id=${active.id}`, {
        query: DEFAULT_QUERY,
      });
      await refreshProjects();
      setMessage("Agent step recorded for the active project.");
    });
  }

  async function approveRun(run: AgentRun) {
    if (!active) return;
    await withAction(`approve-${run.id}`, async () => {
      await postApi(`/api/v1/agent-runs/${run.id}/approve?project_id=${active.id}`, {});
      await refreshProjects();
      setMessage("Approval recorded for the supervised run.");
    });
  }

  async function loadAudit(run: AgentRun) {
    if (!active) return;
    await withAction(`audit-${run.id}`, async () => {
      const result = await api<AgentAudit>(`/api/v1/agent-runs/${run.id}/audit?project_id=${active.id}`);
      setAudit(result);
      setMessage("Audit details loaded.");
    });
  }

  async function startCheckout() {
    const teamId = session?.team?.id;
    if (!teamId) {
      setErrorMessage("Sign in before starting checkout.");
      return;
    }
    await withAction("checkout", async () => {
      const checkout = await postApi<CheckoutResponse>("/api/v1/billing/checkout", {
        team_id: teamId,
        tier: "pro",
        success_url: window.location.href,
        cancel_url: window.location.href,
      });
      setMessage(`Checkout ready: ${checkout.url}`);
    });
  }

  async function logout() {
    await withAction("logout", async () => {
      await postApi("/api/v1/auth/logout", {});
      await refreshSession();
      setMessage("Signed out.");
    });
  }

  return (
    <main className="min-h-screen bg-[#f6f4ef] text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="grid gap-4 border-b border-slate-300 pb-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">V2/V3 Research OS</p>
            <h1 className="mt-1 text-3xl font-bold">AI Scientist Workspace</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Multi-user research operations with evidence, experiment planning, supervised agents, billing, jobs, storage, and
              platform health.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold" href="/legacy">
              Legacy UI
            </a>
            <button
              className="rounded-md bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
              disabled={!session?.team || busyAction === "checkout"}
              onClick={startCheckout}
            >
              {busyAction === "checkout" ? "Preparing..." : "Upgrade"}
            </button>
            {session?.authenticated && (
              <button
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50"
                disabled={busyAction === "logout"}
                onClick={logout}
              >
                {busyAction === "logout" ? "Signing out..." : "Logout"}
              </button>
            )}
          </div>
        </header>

        <StatusStrip
          error={[sessionError, projectsError, healthError].find(Boolean)}
          message={message}
          errorMessage={errorMessage}
          loading={sessionLoading || projectsLoading || healthLoading}
        />

        <section className="grid gap-4 lg:grid-cols-[1.1fr_.9fr]">
          <form className="grid gap-3 rounded-md border border-slate-300 bg-white p-4 md:grid-cols-4" onSubmit={signup}>
            <div className="md:col-span-4">
              <h2 className="text-base font-bold">Session</h2>
              <p className="text-sm text-slate-600">
                {session?.authenticated
                  ? `${session.user?.email ?? "Signed in"} on ${session.team?.name ?? "Local"} as ${session.role ?? "viewer"}`
                  : "Sign up or sign back in to refresh the workspace session."}
              </p>
            </div>
            <input className="rounded-md border border-slate-300 p-2 text-sm" name="email" placeholder="email" defaultValue="owner@example.com" />
            <input
              className="rounded-md border border-slate-300 p-2 text-sm"
              name="password"
              placeholder="password"
              type="password"
              defaultValue="password123"
            />
            <input className="rounded-md border border-slate-300 p-2 text-sm" name="team_name" placeholder="team" defaultValue="Research Lab" />
            <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50" disabled={busyAction === "auth"}>
              {busyAction === "auth" ? "Refreshing..." : "Sign up / refresh"}
            </button>
          </form>

          <form className="grid gap-3 rounded-md border border-slate-300 bg-white p-4" onSubmit={createProject}>
            <div>
              <h2 className="text-base font-bold">Active Project</h2>
              <p className="text-sm text-slate-600">Choose the project that drives every panel below.</p>
            </div>
            <select
              className="rounded-md border border-slate-300 p-2 text-sm"
              disabled={!projects?.length}
              value={active?.id ?? ""}
              onChange={(event) => {
                setActiveProjectId(event.target.value);
                setAudit(null);
              }}
            >
              {(projects ?? []).map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
              <input className="rounded-md border border-slate-300 p-2 text-sm" name="project_name" placeholder="New project name" />
              <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold" disabled={busyAction === "project"}>
                Create
              </button>
            </div>
          </form>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric title="Projects" value={projects?.length ?? 0} detail="available workspaces" />
          <Metric title="Briefs" value={active?.briefs?.length ?? 0} detail="generated syntheses" />
          <Metric title="Evidence" value={evidence.length} detail="claims in latest brief" />
          <Metric title="Plans" value={active?.experiment_plans?.length ?? 0} detail="experiment design packs" />
          <Metric title="Agents" value={active?.autonomous_agents?.length ?? 0} detail="supervised workflows" />
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
          <div className="grid gap-6">
            <WorkspacePanel title="Evidence" meta={active?.name ?? "No active project"}>
              {projectsLoading ? (
                <EmptyState text="Loading project evidence..." />
              ) : evidence.length ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {evidence.slice(0, 8).map((item) => (
                    <EvidenceCard item={item} key={item.id} />
                  ))}
                </div>
              ) : (
                <EmptyState text="Run a research question from the legacy UI or API to populate citation-grounded evidence." />
              )}
            </WorkspacePanel>

            <WorkspacePanel title="Experiment Plans" meta={`${active?.experiment_plans?.length ?? 0} total`}>
              {active?.experiment_plans?.length ? (
                <div className="grid gap-3">
                  {active.experiment_plans.slice(0, 5).map((plan) => (
                    <article className="rounded-md border border-slate-200 bg-slate-50 p-4" key={plan.id}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <h3 className="max-w-2xl text-sm font-bold">{plan.title}</h3>
                        <StatusBadge value={plan.status} />
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{plan.objective}</p>
                      <p className="mt-3 text-xs text-slate-500">
                        {(plan.datasets?.length ?? 0)} datasets / {(plan.baselines?.length ?? 0)} baselines / {(plan.metrics?.length ?? 0)} metrics
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState text="No experiment plans yet. Generate one from a research brief in the legacy workflow." />
              )}
            </WorkspacePanel>

            <WorkspacePanel title="Artifacts" meta={`${active?.execution_artifacts?.length ?? 0} run outputs`}>
              {active?.execution_artifacts?.length ? (
                <div className="grid gap-3">
                  {active.execution_artifacts.slice(0, 5).map((artifact) => (
                    <article className="rounded-md border border-slate-200 bg-slate-50 p-4" key={artifact.id}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <StatusBadge value={artifact.kind} />
                        <span className="text-xs text-slate-500">{artifact.run_id}</span>
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{artifact.content || artifact.path || "Stored artifact"}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState text="Sandbox runs, exports, uploaded PDFs, and generated scripts will appear as stored production artifacts." />
              )}
            </WorkspacePanel>
          </div>

          <aside className="grid gap-6">
            <WorkspacePanel title="Agents And Approvals" meta={`${agentRuns.length} runs`}>
              <div className="mb-4 flex flex-wrap gap-2">
                <button
                  className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  disabled={!active || busyAction === "literature_monitor"}
                  onClick={() => createAgent("literature_monitor")}
                >
                  {busyAction === "literature_monitor" ? "Creating..." : "Monitor"}
                </button>
                <button
                  className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  disabled={!active || busyAction === "experiment_runner"}
                  onClick={() => createAgent("experiment_runner")}
                >
                  {busyAction === "experiment_runner" ? "Creating..." : "Runner"}
                </button>
                <button
                  className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  disabled={!runnableRun || busyAction === "run-step"}
                  onClick={runAgentStep}
                >
                  {busyAction === "run-step" ? "Running..." : "Run step"}
                </button>
              </div>
              {agentRuns.length ? (
                <div className="grid gap-3">
                  {agentRuns.slice(0, 5).map((run) => (
                    <AgentRunCard
                      busyAction={busyAction}
                      key={run.id}
                      onApprove={() => approveRun(run)}
                      onAudit={() => loadAudit(run)}
                      run={run}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState text="Create a monitor or runner to start supervised autonomous workflow records." />
              )}
              {audit && (
                <pre className="mt-3 max-h-44 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                  {JSON.stringify(audit, null, 2)}
                </pre>
              )}
            </WorkspacePanel>

            <WorkspacePanel title="Notifications" meta={`${active?.notifications?.length ?? 0} latest`}>
              {active?.notifications?.length ? (
                <div className="grid gap-3">
                  {active.notifications.slice(0, 5).map((note) => (
                    <article className="rounded-md border border-slate-200 bg-slate-50 p-3" key={note.id}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-bold">{note.title}</h3>
                        <StatusBadge value={note.status} />
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{note.body}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState text="Agent monitors and saved searches will place user-visible updates here." />
              )}
            </WorkspacePanel>

            <WorkspacePanel title="Platform Health" meta={healthLoading ? "checking" : healthError ? "attention" : "online"}>
              <div className="grid gap-3">
                {["database", "redis_workers", "storage", "sandbox"].map((key) => (
                  <HealthCard
                    expanded={expandedHealth === key}
                    health={health}
                    key={key}
                    name={key}
                    onToggle={() => setExpandedHealth(expandedHealth === key ? "" : key)}
                  />
                ))}
              </div>
            </WorkspacePanel>
          </aside>
        </section>
      </div>
    </main>
  );
}

function StatusStrip({
  error,
  errorMessage,
  loading,
  message,
}: {
  error: unknown;
  errorMessage: string;
  loading: boolean;
  message: string;
}) {
  if (errorMessage) {
    return <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800">{errorMessage}</p>;
  }
  if (error) {
    return <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">Some workspace data could not load.</p>;
  }
  if (message) {
    return <p className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">{message}</p>;
  }
  if (loading) {
    return <p className="rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-600">Loading workspace state...</p>;
  }
  return <p className="rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-600">Workspace ready.</p>;
}

function Metric({ detail, title, value }: { detail: string; title: string; value: number | string }) {
  return (
    <div className="rounded-md border border-slate-300 bg-white p-4">
      <p className="text-sm font-semibold text-slate-600">{title}</p>
      <strong className="mt-1 block truncate text-2xl">{value}</strong>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function WorkspacePanel({ children, meta, title }: { children: ReactNode; meta: string; title: string }) {
  return (
    <section className="rounded-md border border-slate-300 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">{title}</h2>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{meta}</span>
      </div>
      {children}
    </section>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge value={item.extraction_type} />
        <span className="max-w-[12rem] truncate text-xs text-slate-500" title={item.source_id}>
          {item.source_id}
        </span>
      </div>
      <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-800">{item.claim}</p>
    </article>
  );
}

function AgentRunCard({
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
  const pending = run.decisions?.some((decision) => decision.requires_approval && !decision.approved);
  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge value={run.status} />
        <span className="text-xs text-slate-500">{run.decisions?.length ?? 0} decisions</span>
      </div>
      <p className="mt-2 text-sm font-semibold">{run.current_step || "queued"}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold" onClick={onAudit}>
          {busyAction === `audit-${run.id}` ? "Loading..." : "Audit"}
        </button>
        {pending && (
          <button
            className="rounded-md bg-emerald-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
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

function HealthCard({
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
      {expanded && <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(value ?? {}, null, 2)}</pre>}
    </article>
  );
}

function StatusBadge({ value }: { value: string }) {
  return <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold uppercase text-emerald-800">{value || "unknown"}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">{text}</p>;
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
