export type Project = {
  id: string;
  name: string;
  description?: string | null;
  briefs: Brief[];
  memory: unknown[];
  experiment_plans: ExperimentPlan[];
  uploaded_papers?: unknown[];
  autonomous_agents?: AgentDefinition[];
  autonomous_agent_runs?: AgentRun[];
  notifications?: NotificationRecord[];
  execution_artifacts?: ExecutionArtifact[];
};

export type Brief = {
  id: string;
  title: string;
  created_at?: string;
  evidence_items: EvidenceItem[];
};

export type EvidenceItem = {
  id: string;
  source_id: string;
  extraction_type: string;
  claim: string;
};

export type ExperimentPlan = {
  id: string;
  title: string;
  objective: string;
  status: string;
  created_at?: string;
  datasets?: string[];
  baselines?: string[];
  metrics?: string[];
};

export type AgentDefinition = {
  id: string;
  type: string;
  name: string;
  goal: string;
  schedule: string;
  status: string;
};

export type AgentRun = {
  id: string;
  agent_id: string;
  status: string;
  current_step: string;
  steps?: { name: string; status: string; created_at?: string }[];
  decisions: { id: string; action: string; reason: string; requires_approval: boolean; approved: boolean }[];
};

export type NotificationRecord = {
  id: string;
  title: string;
  body: string;
  status: string;
};

export type ExecutionArtifact = {
  id: string;
  kind: string;
  content: string;
};

export type Session = {
  authenticated: boolean;
  user?: { id: string; email: string };
  team?: { id: string; name: string };
  role?: string;
};

export type AdminHealth = {
  database?: Record<string, unknown>;
  redis_workers?: Record<string, unknown>;
  storage?: Record<string, unknown>;
  sandbox?: Record<string, unknown>;
  [key: string]: unknown;
};

export type CheckoutResponse = {
  url: string;
};

export type AgentAudit = {
  run?: AgentRun;
  decisions?: AgentRun["decisions"];
  steps?: AgentRun["steps"];
  artifacts?: ExecutionArtifact[];
  [key: string]: unknown;
};

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function postApi<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
