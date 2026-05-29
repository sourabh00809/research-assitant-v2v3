from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from ._state import BASE_DIR

router = APIRouter(tags=["frontend"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/")
def index() -> HTMLResponse:
    frontend_dir = BASE_DIR / "frontend" / "out"
    if frontend_dir.exists():
        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return RedirectResponse("/app", status_code=307)


@router.get("/legacy")
def legacy_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/app")
def next_app_placeholder() -> HTMLResponse:
    frontend_dir = BASE_DIR / "frontend" / "out"
    if frontend_dir.exists():
        return RedirectResponse("/", status_code=302)
    return HTMLResponse(v2_v3_workspace_html())


def v2_v3_workspace_html() -> str:
    return """
<!doctype html>
<html>
<head>
  <title>Research Assistant Workspace</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body{margin:0;background:#f7f8f5;color:#17211f;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
    main{max-width:1180px;margin:auto;padding:28px;display:grid;gap:22px}
    header{display:flex;justify-content:space-between;align-items:end;gap:16px;border-bottom:1px solid #d9ded8;padding-bottom:18px}
    h1{font-size:34px;margin:0}.eyebrow{font-size:12px;text-transform:uppercase;color:#08735f;font-weight:800;margin:0 0 6px}
    .grid{display:grid;gap:16px}.stats{grid-template-columns:repeat(5,minmax(0,1fr))}.cols{grid-template-columns:1.25fr .75fr}
    .card{background:white;border:1px solid #d9ded8;border-radius:8px;padding:18px}.stat strong{font-size:26px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.stat small{color:#64736f}
    .stat span,.muted{color:#64736f}button,a.button{border:1px solid #16443c;background:white;color:#16443c;border-radius:6px;padding:10px 12px;font-weight:800;text-decoration:none;cursor:pointer}
    button.primary{background:#08735f;color:white;border-color:#08735f}input,select{border:1px solid #cdd5d1;border-radius:6px;padding:10px;font:inherit}
    form{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.list{display:grid;gap:10px}.item{border:1px solid #e1e6e2;border-radius:6px;padding:12px}
    .item p{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.badge{display:inline-block;border-radius:999px;background:#dff5eb;color:#075d4d;padding:4px 8px;font-size:11px;font-weight:800;text-transform:uppercase}.health-card{border:1px solid #e1e6e2;border-radius:6px;padding:12px;background:#f7f8f5}.actions{display:flex;gap:8px;flex-wrap:wrap}
    @media(max-width:820px){.stats,.cols,form{grid-template-columns:1fr}header{align-items:start;flex-direction:column}}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="eyebrow">V2/V3 Research OS</p>
      <h1>Research Assistant Workspace</h1>
      <p class="muted">Multi-user SaaS foundations, agents, approvals, billing, jobs, storage, and platform health.</p>
    </div>
    <div class="actions">
      <a class="button" href="/legacy">Legacy UI</a>
      <button class="primary" onclick="checkout()">Upgrade</button>
    </div>
  </header>
  <form onsubmit="signup(event)">
    <input id="email" value="owner@example.com" placeholder="email" />
    <input id="password" value="password123" placeholder="password" type="password" />
    <input id="team" value="Research Lab" placeholder="team" />
    <button class="primary">Sign up / refresh session</button>
  </form>
  <form onsubmit="createProject(event)">
    <select id="projectSelect" onchange="selectProject(event)"></select>
    <input id="newProjectName" placeholder="New project name" />
    <button>Create project</button>
  </form>
  <section class="grid stats">
    <div class="card stat"><span>Team</span><strong id="teamName">Local</strong><small>signed-in tenant</small></div>
    <div class="card stat"><span>Projects</span><strong id="projectCount">0</strong><small>available workspaces</small></div>
    <div class="card stat"><span>Briefs</span><strong id="briefCount">0</strong><small>generated syntheses</small></div>
    <div class="card stat"><span>Plans</span><strong id="planCount">0</strong><small>experiment packs</small></div>
    <div class="card stat"><span>Agents</span><strong id="agentCount">0</strong><small>supervised workflows</small></div>
  </section>
  <section class="grid cols">
    <div class="grid">
      <div class="card"><h2>Project Workspace</h2><p id="projectName" class="muted">Loading project...</p><div id="evidence" class="list"></div></div>
      <div class="card"><h2>Experiment Plans</h2><div id="plans" class="list"></div></div>
    </div>
    <aside class="grid">
      <div class="card">
        <h2>Agents</h2>
        <div class="actions">
          <button onclick="createAgent('literature_monitor')">Monitor</button>
          <button onclick="createAgent('experiment_runner')">Runner</button>
          <button class="primary" onclick="runAgent()">Run step</button>
        </div>
        <div id="agents" class="list" style="margin-top:12px"></div>
      </div>
      <div class="card"><h2>Notifications</h2><div id="notifications" class="list"></div></div>
      <div class="card"><h2>Platform Health</h2><div id="health" class="list">Loading...</div></div>
    </aside>
  </section>
</main>
<script>
  let state = {projects: [], session: {}, activeProjectId: ''};
  async function api(path, options) {
    const res = await fetch(path, options);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
  async function load() {
    state.session = await api('/api/v1/auth/session');
    state.projects = await api('/api/v1/projects');
    const health = await api('/api/v1/admin/health');
    if (!state.activeProjectId && state.projects.length) state.activeProjectId = state.projects[0].id;
    const p = state.projects.find(project => project.id === state.activeProjectId) || state.projects[0] || {};
    projectSelect.innerHTML = state.projects.map(project => `<option value="${project.id}" ${project.id === p.id ? 'selected' : ''}>${project.name}</option>`).join('');
    teamName.textContent = state.session.team?.name || 'Local';
    projectCount.textContent = state.projects.length || 0;
    briefCount.textContent = (p.briefs || []).length;
    planCount.textContent = (p.experiment_plans || []).length;
    agentCount.textContent = (p.autonomous_agents || []).length;
    projectName.textContent = p.name || 'No project yet';
    renderHealth(health);
    renderList('evidence', ((p.briefs || [])[0]?.evidence_items || []).slice(0, 6), x => `<span class="badge">${x.extraction_type}</span><p>${x.claim}</p><small>${x.source_id}</small>`, 'Run a question to populate evidence.');
    renderList('plans', (p.experiment_plans || []).slice(0, 4), x => `<b>${x.title}</b><p>${x.objective}</p><small>${x.status}</small>`, 'No experiment plans yet.');
    renderList('agents', (p.autonomous_agent_runs || []).slice(0, 5), x => `<span class="badge">${x.status}</span><p>${x.current_step}</p><small>${(x.decisions || []).length} decisions</small>${hasPendingApproval(x) ? `<div class="actions"><button onclick="approveRun('${x.id}')">Approve</button></div>` : ''}`, 'No agent runs yet.');
    renderList('notifications', (p.notifications || []).slice(0, 5), x => `<b>${x.title}</b><p>${x.body}</p>`, 'No notifications yet.');
  }
  function renderList(id, items, template, empty) {
    document.getElementById(id).innerHTML = items.length ? items.map(x => `<article class="item">${template(x)}</article>`).join('') : `<p class="muted">${empty}</p>`;
  }
  function renderHealth(health) {
    const keys = ['database', 'redis_workers', 'storage', 'sandbox'];
    document.getElementById('health').innerHTML = keys.map(key => {
      const value = health[key] || {};
      return `<article class="health-card"><b>${key.replace('_',' ')}</b><p class="muted">${value.status || value.backend || 'unknown'}</p></article>`;
    }).join('');
  }
  function activeProject() {
    return state.projects.find(project => project.id === state.activeProjectId) || state.projects[0];
  }
  function hasPendingApproval(run) {
    return (run.decisions || []).some(decision => decision.requires_approval && !decision.approved);
  }
  function selectProject(event) {
    state.activeProjectId = event.target.value;
    load();
  }
  async function createProject(event) {
    event.preventDefault();
    const name = newProjectName.value.trim(); if (!name) return;
    const project = await api('/api/v1/projects', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({name,description:'V2/V3 beta smoke workspace.'})});
    state.activeProjectId = project.id;
    newProjectName.value = '';
    await load();
  }
  async function signup(event) {
    event.preventDefault();
    try {
      await api('/api/v1/auth/signup', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({email:email.value,password:password.value,team_name:team.value})});
    } catch (e) {
      await api('/api/v1/auth/login', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({email:email.value,password:password.value})});
    }
    await load();
  }
  async function createAgent(type) {
    const p = activeProject(); if (!p) return;
    await api(`/api/v1/projects/${p.id}/agents`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({type,name:type.replace('_',' '),goal:'Prepare approved research workflow',schedule:'weekly'})});
    await load();
  }
  async function runAgent() {
    const p = activeProject(); const run = (p?.autonomous_agent_runs || []).find(hasPendingApproval) || p?.autonomous_agent_runs?.[0]; if (!run) return;
    await api(`/api/v1/agent-runs/${run.id}/step?project_id=${p.id}`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({query:'retrieval augmented research agents'})});
    await load();
  }
  async function approveRun(runId) {
    const p = activeProject(); if (!p) return;
    await api(`/api/v1/agent-runs/${runId}/approve?project_id=${p.id}`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({})});
    await load();
  }
  async function checkout() {
    const teamId = state.session.team?.id || 'local';
    const result = await api('/api/v1/billing/upgrade', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({team_id:teamId,tier:'pro'})});
    alert('Upgraded to: ' + result.subscription.tier);
  }
  load();
</script>
</body>
</html>
"""
