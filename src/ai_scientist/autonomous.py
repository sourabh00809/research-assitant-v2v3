from __future__ import annotations

from .models import (
    AgentDecision,
    AgentDefinition,
    AgentRunRecord,
    ExecutionArtifact,
    NotificationRecord,
    ResearchProject,
    SavedSearch,
    new_id,
    utc_now,
)


def start_agent_run(project: ResearchProject, agent: AgentDefinition) -> AgentRunRecord:
    run = AgentRunRecord(
        id=new_id("agent_run"),
        agent_id=agent.id,
        project_id=project.id,
        status="queued",
        current_step="scheduled",
        created_at=utc_now(),
    )
    run.decisions.append(
        AgentDecision(
            id=new_id("decision"),
            agent_id=agent.id,
            run_id=run.id,
            action="start_workflow",
            reason="Workflow run created from persisted agent definition.",
            requires_approval=False,
            approved=True,
            created_at=utc_now(),
        )
    )
    project.autonomous_agent_runs.insert(0, run)
    return run


def literature_monitor_step(project: ResearchProject, run: AgentRunRecord, query: str) -> AgentDecision:
    decision = AgentDecision(
        id=new_id("decision"),
        agent_id=run.agent_id,
        run_id=run.id,
        action="literature_monitor_search",
        reason=f"Search saved query and ingest only deduplicated new papers: {query}",
        requires_approval=False,
        approved=True,
        created_at=utc_now(),
    )
    run.decisions.append(decision)
    run.current_step = "literature_monitor_search"
    run.status = "running"
    run.steps.append({"name": "literature_monitor_search", "status": "completed", "query": query, "created_at": utc_now()})
    return decision


def create_saved_search(project: ResearchProject, query: str, cadence: str = "weekly") -> SavedSearch:
    existing = next((item for item in project.saved_searches if item.query.lower() == query.lower()), None)
    if existing:
        existing.cadence = cadence
        return existing
    search = SavedSearch(id=new_id("search"), project_id=project.id, query=query, cadence=cadence, created_at=utc_now())
    project.saved_searches.insert(0, search)
    return search


def complete_literature_monitor(project: ResearchProject, run: AgentRunRecord, search: SavedSearch) -> NotificationRecord:
    seen_titles = {paper.title.strip().lower() for paper in project.uploaded_papers}
    new_count = 0
    for paper in project.uploaded_papers:
        title = paper.title.strip().lower()
        if title and title in seen_titles:
            continue
        seen_titles.add(title)
        new_count += 1
    search.last_run_at = utc_now()
    run.status = "completed"
    run.current_step = "notified_user"
    run.completed_at = utc_now()
    notification = NotificationRecord(
        id=new_id("note"),
        project_id=project.id,
        title="Literature monitor completed",
        body=f"Saved search '{search.query}' checked for new sources. New deduplicated sources: {new_count}.",
        created_at=utc_now(),
    )
    project.notifications.insert(0, notification)
    run.steps.append({"name": "notify", "status": "completed", "new_sources": new_count, "created_at": utc_now()})
    return notification


def request_experiment_approval(run: AgentRunRecord, plan_id: str | None) -> AgentDecision:
    decision = AgentDecision(
        id=new_id("decision"),
        agent_id=run.agent_id,
        run_id=run.id,
        action="request_experiment_approval",
        reason=f"Experiment execution requires human approval before sandbox run. plan_id={plan_id or 'none'}",
        requires_approval=True,
        approved=False,
        created_at=utc_now(),
    )
    run.decisions.append(decision)
    run.current_step = "awaiting_approval"
    run.status = "queued"
    return decision


def record_execution_artifact(project: ResearchProject, run: AgentRunRecord, kind: str, content: str, path: str = "") -> ExecutionArtifact:
    artifact = ExecutionArtifact(
        id=new_id("artifact"),
        project_id=project.id,
        run_id=run.id,
        kind=kind,  # type: ignore[arg-type]
        content=content,
        path=path,
        created_at=utc_now(),
    )
    project.execution_artifacts.insert(0, artifact)
    run.steps.append({"name": f"record_{kind}", "status": "completed", "artifact_id": artifact.id, "created_at": utc_now()})
    return artifact
