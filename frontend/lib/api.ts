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
  confidence?: number;
  retrieval_method?: string;
  semantic_score?: number;
  source_quote?: string;
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
  run_id?: string;
  path?: string;
};

export type Session = {
  authenticated: boolean;
  user?: { id: string; email: string };
  team?: { id: string; name: string };
  subscription?: { tier: string; status: string };
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

let _csrfToken = "";

function getCookies(): Record<string, string> {
  return Object.fromEntries(
    document.cookie.split("; ").filter(Boolean).map((c) => {
      const idx = c.indexOf("=");
      return [c.slice(0, idx), c.slice(idx + 1)];
    })
  );
}

function getCsrfHeader(): Record<string, string> {
  if (!_csrfToken) {
    _csrfToken = getCookies()["csrf-token"] || "";
  }
  return _csrfToken ? { "x-csrf-token": _csrfToken } : {};
}

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "include" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  _csrfToken = getCookies()["csrf-token"] || _csrfToken;
  return response.json();
}

export async function postApi<T>(path: string, body: unknown): Promise<T> {
  return _fetchJson<T>("POST", path, body);
}

export async function patchApi<T>(path: string, body: unknown): Promise<T> {
  return _fetchJson<T>("PATCH", path, body);
}

export async function putApi<T>(path: string, body: unknown): Promise<T> {
  return _fetchJson<T>("PUT", path, body);
}

export async function deleteApi(path: string): Promise<void> {
  const headers: Record<string, string> = {};
  Object.assign(headers, getCsrfHeader());
  const response = await fetch(path, { method: "DELETE", credentials: "include", headers });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  _csrfToken = getCookies()["csrf-token"] || _csrfToken;
}

async function _fetchJson<T>(method: string, path: string, body: unknown): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  Object.assign(headers, getCsrfHeader());
  const response = await fetch(path, {
    method,
    credentials: "include",
    headers,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  _csrfToken = getCookies()["csrf-token"] || _csrfToken;
  return response.json();
}
