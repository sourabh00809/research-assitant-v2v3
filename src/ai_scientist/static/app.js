let state = {
  projects: [],
  activeProjectId: null,
  latestRun: null,
  latestBriefId: null,
  latestPlanId: null,
  latestGraph: null,
  connectors: [],
};

const el = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    if (response.status === 401) throw new Error("Unauthorized. Log in again to continue.");
    throw new Error(formatError(detail, response.status));
  }
  return response.json();
}

async function init() {
  try {
    await api("/api/health");
    el("healthStatus").textContent = "API online";
  } catch {
    el("healthStatus").textContent = "API unavailable";
  }

  await loadProjects();
  await loadConnectors();
  bindEvents();
}

function bindEvents() {
  el("createProject").addEventListener("click", createProject);
  el("questionForm").addEventListener("submit", runQuestion);
  el("memoryForm").addEventListener("submit", saveMemory);
  el("paperForm").addEventListener("submit", uploadPaper);
  el("planButton").addEventListener("click", generateExperimentPlan);
  el("recommendPlanButton").addEventListener("click", recommendExperimentPlan);
  el("scriptButton").addEventListener("click", generatePlanScript);
  el("hypothesisButton").addEventListener("click", generateHypotheses);
  el("graphButton").addEventListener("click", refreshGraph);
  document.addEventListener("click", handlePromoteClick);
}

async function handlePromoteClick(event) {
  const button = event.target.closest("[data-promote-memory]");
  if (!button) return;
  const project = activeProject();
  if (!project) return;
  button.disabled = true;
  try {
    const updated = await api(`/api/projects/${project.id}/memory/promote`, {
      method: "POST",
      body: JSON.stringify({
        kind: button.dataset.kind || "claim",
        content: button.dataset.content || "",
        source_ids: button.dataset.sourceId ? [button.dataset.sourceId] : [],
        tags: ["review-queue"],
      }),
    });
    upsertProject(updated);
    renderProjects();
    renderActiveProject();
  } catch (error) {
    button.textContent = "Failed";
  } finally {
    button.disabled = false;
  }
}

async function loadProjects() {
  state.projects = await api("/api/projects");
  if (!state.activeProjectId && state.projects.length) {
    state.activeProjectId = state.projects[0].id;
  }
  renderProjects();
  renderActiveProject();
}

async function loadConnectors() {
  try {
    state.connectors = await api("/api/connectors/status");
  } catch {
    state.connectors = [];
  }
  renderConnectors();
}

async function createProject() {
  const name = el("projectName").value.trim();
  if (!name) return;
  const project = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: "Citation-grounded research workspace." }),
  });
  state.projects.unshift(project);
  state.activeProjectId = project.id;
  el("projectName").value = "";
  renderProjects();
  renderActiveProject();
}

async function runQuestion(event) {
  event.preventDefault();
  const project = activeProject();
  const question = el("questionInput").value.trim();
  const maxPapers = Number(el("maxPapers").value || 6);
  if (!project || !question) return;

  el("runButton").disabled = true;
  el("runStatus").textContent = "Running";
  el("agentSteps").innerHTML = `<div class="step"><strong>Agent run started</strong><p>Searching and extracting evidence...</p></div>`;

  try {
    const result = await api(`/api/projects/${project.id}/questions/run`, {
      method: "POST",
      body: JSON.stringify({ question, max_papers: maxPapers, use_memory: true }),
    });
    state.latestRun = result.run;
    upsertProject(result.project);
    state.activeProjectId = result.project.id;
    renderProjects();
    renderActiveProject(result.brief, result.run);
  } catch (error) {
    el("agentSteps").innerHTML = `<div class="step"><strong>Run failed</strong><p>${escapeHtml(error.message)}</p></div>`;
    el("runStatus").textContent = "Failed";
  } finally {
    el("runButton").disabled = false;
  }
}

async function saveMemory(event) {
  event.preventDefault();
  const project = activeProject();
  const content = el("memoryContent").value.trim();
  if (!project || !content) return;
  const tags = el("memoryTags").value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  const updated = await api(`/api/projects/${project.id}/memory`, {
    method: "POST",
    body: JSON.stringify({
      kind: el("memoryKind").value,
      content,
      tags,
      source_ids: [],
    }),
  });
  upsertProject(updated);
  el("memoryContent").value = "";
  el("memoryTags").value = "";
  renderProjects();
  renderActiveProject();
}

async function uploadPaper(event) {
  event.preventDefault();
  const project = activeProject();
  const file = el("paperFile").files[0];
  if (!project || !file) return;
  el("paperList").innerHTML = `<div class="empty">Uploading and extracting text...</div>`;
  try {
    const form = new FormData();
    form.append("file", file);
    await fetch(`/api/projects/${project.id}/papers/upload?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      body: form,
    }).then(async (response) => {
      if (!response.ok) throw new Error(formatError(await response.text(), response.status));
      return response.json();
    });
    const refreshed = await api(`/api/projects/${project.id}`);
    upsertProject(refreshed);
    el("paperFile").value = "";
    renderProjects();
    renderActiveProject();
  } catch (error) {
    el("paperList").innerHTML = `<div class="empty">Upload failed: ${escapeHtml(error.message)}</div>`;
  }
}

async function generateExperimentPlan() {
  const project = activeProject();
  const brief = project?.briefs?.[0];
  if (!project || !brief) return;

  el("planButton").disabled = true;
  el("planOutput").className = "brief-empty";
  el("planOutput").textContent = "Generating experiment design pack...";
  try {
    const updated = await api(`/api/projects/${project.id}/experiment-plans`, {
      method: "POST",
      body: JSON.stringify({ brief_id: brief.id }),
    });
    upsertProject(updated);
    renderProjects();
    renderActiveProject();
  } catch (error) {
    el("planOutput").textContent = `Plan generation failed: ${error.message}`;
  } finally {
    el("planButton").disabled = false;
  }
}

async function recommendExperimentPlan() {
  const project = activeProject();
  const brief = project?.briefs?.[0];
  if (!project || !brief) return;
  el("planRecommendation").innerHTML = `<div class="empty">Ranking datasets, baselines, metrics, and validation helpers...</div>`;
  try {
    const recommendation = await api(`/api/projects/${project.id}/experiment-plans/recommend`, {
      method: "POST",
      body: JSON.stringify({ brief_id: brief.id, question: brief.title, top_k: 5 }),
    });
    el("planRecommendation").innerHTML = `
      ${section("Template", [`${recommendation.template_id} (${recommendation.domain}/${recommendation.task})`])}
      ${section("Recommended Datasets", (recommendation.datasets || []).map(formatRecommendation))}
      ${section("Recommended Baselines", (recommendation.baselines || []).map(formatRecommendation))}
      ${section("Recommended Metrics", (recommendation.metrics || []).map(formatRecommendation))}
      ${section("Validation", [recommendation.validation])}
    `;
  } catch (error) {
    el("planRecommendation").innerHTML = `<div class="empty">Recommendation failed: ${escapeHtml(error.message)}</div>`;
  }
}

async function generatePlanScript() {
  const project = activeProject();
  const plan = project?.experiment_plans?.[0];
  if (!project || !plan) return;
  el("scriptButton").disabled = true;
  try {
    const updatedPlan = await api(`/api/projects/${project.id}/experiment-plans/${plan.id}/generate-script`, {
      method: "POST",
      body: JSON.stringify({ validation_tests: ["paired_t_test", "wilcoxon"], confidence_interval: "bootstrap", correction: "fdr" }),
    });
    const refreshed = await api(`/api/projects/${project.id}`);
    upsertProject(refreshed);
    renderProjects();
    renderActiveProject(null, state.latestRun);
    el("planRecommendation").innerHTML = `<div class="empty">Script regenerated for ${escapeHtml(updatedPlan.title)}.</div>`;
  } catch (error) {
    el("planRecommendation").innerHTML = `<div class="empty">Script generation failed: ${escapeHtml(error.message)}</div>`;
  } finally {
    el("scriptButton").disabled = false;
  }
}

async function generateHypotheses() {
  const project = activeProject();
  const brief = project?.briefs?.[0];
  if (!project || !brief) return;

  el("hypothesisButton").disabled = true;
  try {
    const plan = project.experiment_plans?.[0];
    const updated = await api(`/api/projects/${project.id}/hypotheses`, {
      method: "POST",
      body: JSON.stringify({
        brief_id: brief.id,
        experiment_plan_id: plan?.id || null,
        max_hypotheses: 4,
      }),
    });
    upsertProject(updated);
    renderProjects();
    renderActiveProject();
    await refreshGraph();
  } catch (error) {
    el("hypothesisList").innerHTML = `<div class="empty">Hypothesis generation failed: ${escapeHtml(error.message)}</div>`;
  } finally {
    el("hypothesisButton").disabled = false;
  }
}

async function refreshGraph() {
  const project = activeProject();
  if (!project) return;
  try {
    state.latestGraph = await api(`/api/projects/${project.id}/graph`);
    renderGraph(state.latestGraph);
  } catch (error) {
    el("graphSummary").textContent = "Graph unavailable";
    el("graphList").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function upsertProject(project) {
  const index = state.projects.findIndex((item) => item.id === project.id);
  if (index >= 0) state.projects[index] = project;
  else state.projects.unshift(project);
}

function activeProject() {
  return state.projects.find((project) => project.id === state.activeProjectId);
}

function renderProjects() {
  el("projectList").innerHTML = state.projects
    .map(
      (project) => `
      <button class="project-card ${project.id === state.activeProjectId ? "active" : ""}" data-project-id="${project.id}">
        <strong>${escapeHtml(project.name)}</strong>
        <p>${project.questions.length} questions &middot; ${project.memory.length} memory items</p>
      </button>
    `
    )
    .join("");

  document.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeProjectId = button.dataset.projectId;
      renderProjects();
      renderActiveProject();
    });
  });
}

function renderActiveProject(forcedBrief = null, forcedRun = null) {
  const project = activeProject();
  if (!project) return;

  el("activeProjectName").textContent = project.name;
  const brief = forcedBrief || project.briefs[0];
  const run = forcedRun || state.latestRun;

  renderMemory(project.memory || []);
  renderPapers(project.uploaded_papers || []);
  renderRun(run);
  renderBrief(brief);
  renderMethodologyIntelligence(brief);
  renderExperimentPlan(project.experiment_plans?.[0]);
  renderHypotheses(project.hypotheses || []);
  renderTasks(project.tasks || []);
  renderGraph(state.latestGraph);
  renderEvidence(brief?.evidence_items || []);
  renderMatrix(brief?.paper_matrix || []);
  renderConnectors();
}

function renderRun(run) {
  if (!run) {
    el("runStatus").textContent = "Idle";
    el("providerStatus").textContent = "deterministic";
    el("runContext").innerHTML = `<div class="empty">Run provider and source warnings appear here.</div>`;
    el("agentSteps").innerHTML = `<div class="step"><strong>No active run</strong><p class="meta">Agent traces will appear here after a question runs.</p></div>`;
    return;
  }
  el("runStatus").textContent = run.status;
  el("providerStatus").textContent = run.provider || "deterministic";
  el("agentSteps").innerHTML = run.steps
    .map(
      (step) => `
      <div class="step">
        <strong>${escapeHtml(step.name)} <span class="tag">${escapeHtml(step.status)}</span></strong>
        <p>${escapeHtml(step.summary)}</p>
      </div>
    `
    )
    .join("");
  el("runContext").innerHTML = `
    ${section("Provider", [run.provider || "deterministic"])}
    ${section("Retrieval", ["hybrid semantic + keyword ranking", ...(run.steps?.[2]?.output?.rankings || []).slice(0, 3).map((item) => `${item.source_id}: ${item.score} ${item.reason}`)])}
    ${section("Warnings", run.warnings || [])}
  `;
}

function renderPapers(papers) {
  const embedded = papers.filter((paper) => paper.embedding_status === "embedded").length;
  el("paperCount").textContent = `${papers.length} papers · ${embedded} embedded`;
  el("paperList").innerHTML =
    papers
      .map(
        (paper) => `
      <div class="paper-item">
        <strong>${escapeHtml(paper.title)} <span class="tag">${escapeHtml(paper.status)}</span> <span class="tag">${escapeHtml(paper.embedding_status || "pending")}</span></strong>
        <p>${escapeHtml(paper.filename)}</p>
        <span class="meta">${paper.page_count} pages &middot; ${paper.chunk_count} chunks &middot; ${countExtractions(paper.extractions)} extractions</span>
      </div>
    `
      )
      .join("") || `<div class="empty">No uploaded PDFs yet.</div>`;
}

function renderMemory(memory) {
  el("memoryCount").textContent = `${memory.length} items`;
  el("memoryList").innerHTML =
    memory
      .slice(0, 12)
      .map(
        (item) => `
        <div class="memory-item">
          <strong>${escapeHtml(item.kind.replace("_", " "))}</strong>
          <p>${escapeHtml(item.content)}</p>
          <span class="meta">${escapeHtml((item.tags || []).join(", ")) || "untagged"} &middot; ${new Date(item.created_at).toLocaleString()}</span>
        </div>
      `
      )
      .join("") || `<div class="empty">No memory yet.</div>`;
}

function renderBrief(brief) {
  if (!brief) {
    el("briefTimestamp").textContent = "No brief yet";
    el("exportBrief").classList.add("disabled");
    el("exportBrief").setAttribute("aria-disabled", "true");
    el("exportBrief").setAttribute("href", "#");
    el("planButton").disabled = true;
    el("hypothesisButton").disabled = true;
    el("briefOutput").className = "brief-empty";
    el("briefOutput").textContent = "Run a research question to generate a citation-grounded brief, evidence panel, and paper matrix.";
    return;
  }

  const project = activeProject();
  state.latestBriefId = brief.id;
  el("exportBrief").classList.remove("disabled");
  el("exportBrief").setAttribute("aria-disabled", "false");
  el("exportBrief").setAttribute("href", `/api/projects/${project.id}/briefs/${brief.id}/export.md`);
  el("planButton").disabled = false;
  el("hypothesisButton").disabled = false;
  el("briefTimestamp").textContent = new Date(brief.created_at).toLocaleString();
  el("briefOutput").className = "brief-output";
  el("briefOutput").innerHTML = `
    ${section("Interpretation", [brief.question_interpretation])}
    ${section("Provider Summary", brief.provider_summary ? [brief.provider_summary] : [])}
    ${qualitySection(brief.quality_report)}
    ${section("Key Findings", brief.key_findings)}
    ${section("Methodology Assessment", brief.methodology_assessment)}
    ${section("Weak Evidence Flags", brief.weak_evidence_flags)}
    ${section("Unsupported Claims", brief.unsupported_claims || [])}
    ${section("Speculative Suggestions", brief.speculative_suggestions || [])}
    ${section("Memory Context Used", brief.memory_context_used || [])}
    ${memoryRelevanceSection(brief.memory_relevance_scores || [])}
    ${section("Sources Used", brief.source_modes_used || [])}
    ${section("Provider Used", [brief.provider_used || "deterministic"])}
    ${section("Open Problems", brief.open_problems)}
    ${section("Next Directions", brief.suggested_next_directions)}
    ${section("Bibliography", brief.bibliography)}
  `;
}

function renderHypotheses(hypotheses) {
  el("hypothesisCount").textContent = `${hypotheses.length} items`;
  el("hypothesisList").innerHTML =
    hypotheses
      .slice(0, 8)
      .map(
        (item) => `
      <div class="hypothesis-item">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.statement)}</p>
        <div class="score-row">
          <span class="tag">Novelty ${escapeHtml(item.novelty_score)}</span>
          <span class="tag">Testability ${escapeHtml(item.testability_score)}</span>
        </div>
        <p class="meta">${escapeHtml(item.next_test)}</p>
      </div>
    `
      )
      .join("") || `<div class="empty">No hypotheses generated yet.</div>`;
}

function renderGraph(graph) {
  if (!graph) {
    el("graphSummary").textContent = "Refresh the graph after creating research artifacts.";
    el("graphList").innerHTML = `<div class="empty">No graph loaded yet.</div>`;
    return;
  }
  const counts = graph.nodes.reduce((acc, node) => {
    acc[node.kind] = (acc[node.kind] || 0) + 1;
    return acc;
  }, {});
  el("graphSummary").innerHTML = `
    <div class="graph-metrics">
      <span class="tag">${graph.nodes.length} nodes</span>
      <span class="tag">${graph.edges.length} edges</span>
      ${Object.entries(counts)
        .map(([kind, count]) => `<span class="tag">${escapeHtml(kind)} ${count}</span>`)
        .join("")}
    </div>
  `;
  el("graphList").innerHTML =
    graph.edges
      .slice(0, 16)
      .map(
        (edge) => `
      <div class="graph-edge">
        <span>${escapeHtml(edge.source)}</span>
        <strong>${escapeHtml(edge.relation)}</strong>
        <span>${escapeHtml(edge.target)}</span>
      </div>
    `
      )
      .join("") || `<div class="empty">No graph edges yet.</div>`;
}

function renderExperimentPlan(plan) {
  const project = activeProject();
  if (!plan) {
    state.latestPlanId = null;
    el("planTimestamp").textContent = "No plan yet";
    el("exportPlan").classList.add("disabled");
    el("exportPlan").setAttribute("aria-disabled", "true");
    el("exportPlan").setAttribute("href", "#");
    el("scriptButton").disabled = true;
    el("planOutput").className = "brief-empty";
    el("planOutput").textContent = "Generate an experiment plan after creating a research brief.";
    return;
  }
  state.latestPlanId = plan.id;
  el("planTimestamp").textContent = new Date(plan.created_at).toLocaleString();
  el("exportPlan").classList.remove("disabled");
  el("exportPlan").setAttribute("aria-disabled", "false");
  el("exportPlan").setAttribute("href", `/api/projects/${project.id}/experiment-plans/${plan.id}/export.md`);
  el("scriptButton").disabled = false;
  el("planOutput").className = "brief-output";
  el("planOutput").innerHTML = `
    ${section("Objective", [plan.objective])}
    ${section("Hypothesis", [plan.hypothesis])}
    ${section("Domain", [`${plan.domain || "general"} / ${plan.task || "research_evaluation"}`])}
    ${section("Datasets", (plan.datasets || []).map(formatRecommendation))}
    ${section("Baselines", (plan.baselines || []).map(formatRecommendation))}
    ${section("Metrics", (plan.metrics || []).map(formatRecommendation))}
    ${section("Ablations", plan.ablations || plan.ablation_config?.variables || [])}
    ${section("Validation", plan.statistical_validation || [plan.validation_plan?.strategy].filter(Boolean))}
    ${section("Risks", plan.risks)}
    <div class="brief-section">
      <h4>Generated Script</h4>
      <a class="ghost-link" href="/api/projects/${project.id}/experiment-plans/${plan.id}/script.py">Download Python</a>
      <pre class="code-block"><code>${escapeHtml(plan.generated_script || plan.implementation_template)}</code></pre>
    </div>
  `;
}

function renderTasks(tasks) {
  el("taskCount").textContent = `${tasks.length} tasks`;
  el("taskList").innerHTML =
    tasks
      .slice(0, 8)
      .map(
        (task) => `
      <div class="task-item">
        <strong>${escapeHtml(task.title)} <span class="tag">${escapeHtml(task.status)}</span></strong>
        <p>${escapeHtml(task.summary || task.kind)}</p>
        <span class="meta">${escapeHtml(task.kind)} &middot; ${new Date(task.created_at).toLocaleString()}</span>
      </div>
    `
      )
      .join("") || `<div class="empty">No research tasks yet.</div>`;
}

function renderMethodologyIntelligence(brief) {
  const baselines = brief?.baseline_recommendations || [];
  const validation = brief?.statistical_validation || [];
  el("baselineCount").textContent = `${baselines.length} items`;
  el("validationCount").textContent = `${validation.length} items`;
  el("baselineList").innerHTML = renderCritiqueItems(baselines, "No baseline critique yet.");
  el("validationList").innerHTML = renderCritiqueItems(validation, "No validation recommendations yet.");
}

function renderCritiqueItems(items, emptyText) {
  return (
    items
      .map(
        (item) => `
      <div class="critique-item">
        <p>${escapeHtml(item)}</p>
      </div>
    `
      )
      .join("") || `<div class="empty">${escapeHtml(emptyText)}</div>`
  );
}

function renderEvidence(evidence) {
  el("evidenceCount").textContent = `${evidence.length} claims`;
  el("evidenceList").innerHTML =
    evidence
      .map(
        (item) => `
      <div class="evidence-item" data-confidence="${escapeHtml(item.confidence)}">
        <strong>${escapeHtml(item.extraction_type)} &middot; ${escapeHtml(item.confidence)} confidence</strong>
        <div class="score-row">
          <span class="tag">${escapeHtml(item.retrieval_method || "keyword")}</span>
          ${item.semantic_score !== null && item.semantic_score !== undefined ? `<span class="tag">sim ${escapeHtml(Number(item.semantic_score).toFixed(2))}</span>` : ""}
          ${item.keyword_score !== null && item.keyword_score !== undefined ? `<span class="tag">kw ${escapeHtml(Number(item.keyword_score).toFixed(2))}</span>` : ""}
          ${(item.source_badges || [item.source_type]).filter(Boolean).map((badge) => `<span class="tag">${escapeHtml(badge)}</span>`).join("")}
        </div>
        <p>${escapeHtml(item.claim)}</p>
        <span class="meta">Source: ${escapeHtml(item.source_id)}${item.page_number ? ` &middot; page ${escapeHtml(item.page_number)}` : ""}${item.chunk_id ? ` &middot; chunk ${escapeHtml(item.chunk_id)}` : ""}${item.source_quote ? ` &middot; quote: ${escapeHtml(item.source_quote.slice(0, 140))}` : ""}</span>
        <button class="mini-button" type="button" data-promote-memory data-kind="${memoryKindForEvidence(item.extraction_type)}" data-source-id="${escapeHtml(item.source_id)}" data-content="${escapeHtml(item.claim)}">Promote</button>
      </div>
    `
      )
      .join("") || `<div class="empty">No evidence extracted yet.</div>`;
}

function renderMatrix(rows) {
  el("matrixCount").textContent = `${rows.length} rows`;
  if (!rows.length) {
    el("paperMatrix").innerHTML = `<div class="empty">No paper matrix yet.</div>`;
    return;
  }
  el("paperMatrix").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Source</th>
          <th>Score</th>
          <th>Method</th>
          <th>Dataset</th>
          <th>Metrics</th>
          <th>Baselines</th>
          <th>Validation</th>
          <th>Limitations</th>
          <th>Future Work</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
          <tr>
            <td>${escapeHtml(row.source_id)}</td>
            <td><span class="score">${escapeHtml(row.quality_score ?? 0)}</span></td>
            <td>${escapeHtml(row.method)}</td>
            <td>${escapeHtml(row.dataset)}</td>
            <td>${escapeHtml(row.metrics)}</td>
            <td>${escapeHtml(row.baselines)}</td>
            <td>${escapeHtml(row.validation)}</td>
            <td>${escapeHtml(row.limitations)}</td>
            <td>${escapeHtml(row.future_work)}</td>
          </tr>
        `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function section(title, items) {
  if (!items.length) return "";
  return `
    <div class="brief-section">
      <h4>${escapeHtml(title)}</h4>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function qualitySection(report) {
  if (!report) return "";
  return `
    <div class="brief-section">
      <h4>Brief Quality Report</h4>
      <ul>
        <li>${escapeHtml(report.summary)}</li>
        <li>Citation coverage: ${escapeHtml(Math.round((report.citation_coverage || 0) * 100))}%</li>
        <li>Missing datasets: ${escapeHtml((report.missing_datasets || []).length)}</li>
        <li>Missing baselines: ${escapeHtml((report.missing_baselines || []).length)}</li>
        <li>Missing metrics: ${escapeHtml((report.missing_metrics || []).length)}</li>
        <li>Missing validation: ${escapeHtml((report.missing_statistical_validation || []).length)}</li>
        <li>Retrieval quality: ${escapeHtml(report.hybrid_hits || 0)} hybrid, ${escapeHtml(report.semantic_hits || 0)} semantic, ${escapeHtml(report.keyword_hits || 0)} keyword-only</li>
        <li>Embedding coverage: ${escapeHtml(Math.round((report.embedding_coverage || 0) * 100))}%</li>
        <li>Connectors used: ${escapeHtml((report.connectors_used || []).join(", ") || "none")}</li>
      </ul>
    </div>
  `;
}

function memoryRelevanceSection(scores) {
  if (!scores.length) return "";
  return `
    <div class="brief-section">
      <h4>Memory Relevance</h4>
      <ul>
        ${scores
          .map(
            (item) =>
              `<li>${escapeHtml(item.memory_item_id)} · ${escapeHtml(item.influence)} · sim ${escapeHtml(Number(item.similarity_score || 0).toFixed(2))}</li>`
          )
          .join("")}
      </ul>
    </div>
  `;
}

function renderConnectors() {
  const target = el("connectorList");
  if (!target) return;
  target.innerHTML =
    (state.connectors || [])
      .map(
        (connector) => `
      <div class="connector-row">
        <span>${escapeHtml(connector.source_type)}</span>
        <strong>${connector.enabled ? "on" : "off"}</strong>
        <small>${escapeHtml(connector.last_result_count || 0)} hits</small>
      </div>
    `
      )
      .join("") || `<div class="empty">Connector status unavailable.</div>`;
}
function countExtractions(extractions) {
  if (!extractions) return 0;
  return Object.values(extractions).reduce((total, items) => total + (Array.isArray(items) ? items.length : 0), 0);
}

function formatRecommendation(item) {
  if (typeof item === "string") return item;
  const name = item.name || item.title || "item";
  const detail = [item.source, item.reference, item.formula, item.rationale].filter(Boolean).join(" · ");
  return detail ? `${name} — ${detail}` : name;
}
function memoryKindForEvidence(kind) {
  if (["claim", "method", "dataset", "metric", "baseline"].includes(kind)) return kind;
  if (kind === "limitation" || kind === "future_work" || kind === "assumption") return "gap";
  return "claim";
}

function formatError(detail, status) {
  if (!detail) return `Request failed: ${status}`;
  try {
    const parsed = JSON.parse(detail);
    return parsed.detail || detail;
  } catch {
    return detail;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init();
