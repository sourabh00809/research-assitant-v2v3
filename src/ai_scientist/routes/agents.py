from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..autonomous import (
    complete_literature_monitor,
    literature_monitor_step,
    record_execution_artifact,
    request_experiment_approval,
    start_agent_run,
)
from ..autonomous import (
    create_saved_search as create_saved_search_record,
)
from ..models import (
    AgentDecision,
    AgentDefinition,
    CreateAgentRequest,
    CreateSavedSearchRequest,
    ResearchProject,
    RunAgentStepRequest,
    SandboxRunRequest,
    new_id,
    utc_now,
)
from ..sandbox import run_sandbox
from ._auth import require_project_access
from ._state import state

router = APIRouter(tags=["agents"])


def set_agent_status(project_id: str, agent_id: str, status: str) -> ResearchProject:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agent = next((item for item in project.autonomous_agents if item.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = status
    for run in project.autonomous_agent_runs:
        if run.agent_id == agent_id and run.status in {"queued", "running", "paused"}:
            run.status = "paused" if status == "paused" else "stopped" if status == "stopped" else "running"
            run.current_step = f"agent_{status}"
    return state.store.save_project(project)


@router.post("/api/v1/agents", response_model=ResearchProject)
def create_agent(request: CreateAgentRequest, project_id: str = "") -> ResearchProject:
    project = state.store.get_project(project_id) if project_id else None
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or no default project")
    agent = AgentDefinition(
        id=new_id("agent"),
        project_id=project.id,
        type=request.type,
        name=request.name,
        goal=request.goal,
        schedule=request.schedule,
        created_at=utc_now(),
    )
    project.autonomous_agents.insert(0, agent)
    run = start_agent_run(project, agent)
    if request.type == "experiment_runner":
        request_experiment_approval(run, None)
    return state.store.save_project(project)


@router.post("/api/v1/projects/{project_id}/agents", response_model=ResearchProject)
def create_project_agent(project_id: str, request: CreateAgentRequest, http_request: Request) -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    return create_agent(request, project_id)


@router.post("/api/v1/saved-searches", response_model=ResearchProject)
def create_saved_search(request: CreateSavedSearchRequest, http_request: Request) -> ResearchProject:
    require_project_access(http_request, request.project_id, "member")
    project = state.store.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    create_saved_search_record(project, request.query, request.cadence)
    return state.store.save_project(project)


@router.post("/api/v1/agent-runs/{run_id}/step", response_model=ResearchProject)
def run_agent_step(run_id: str, request: RunAgentStepRequest, http_request: Request, project_id: str = "") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    agent = next((item for item in project.autonomous_agents if item.id == run.agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.type == "literature_monitor":
        search = create_saved_search_record(project, request.query or agent.goal, agent.schedule or "weekly")
        literature_monitor_step(project, run, search.query)
        complete_literature_monitor(project, run, search)
    elif agent.type == "experiment_runner":
        if not request.approve and not any(decision.approved for decision in run.decisions if decision.requires_approval):
            request_experiment_approval(run, request.experiment_plan_id)
        else:
            run.status = "running"
            run.current_step = "ready_for_sandbox"
            run.steps.append({"name": "approval_checked", "status": "completed", "created_at": utc_now()})
    else:
        run.status = "completed"
        run.current_step = "workflow_recorded"
        run.completed_at = utc_now()
        run.steps.append({"name": agent.type, "status": "completed", "created_at": utc_now()})
    return state.store.save_project(project)


@router.post("/api/v1/agent-runs/{run_id}/sandbox", response_model=ResearchProject)
def run_agent_sandbox(run_id: str, request: SandboxRunRequest, http_request: Request, project_id: str = "") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if not any(decision.approved for decision in run.decisions if decision.requires_approval):
        raise HTTPException(status_code=409, detail="Sandbox execution requires an approved agent decision")
    result = run_sandbox(request.script, timeout_seconds=request.timeout_seconds)
    record_execution_artifact(project, run, "stdout", result.get("stdout", ""))
    if result.get("stderr"):
        record_execution_artifact(project, run, "stderr", result["stderr"])
    run.status = "completed" if result["exit_code"] == 0 else "failed"
    run.current_step = "sandbox_completed"
    run.completed_at = utc_now()
    return state.store.save_project(project)


@router.post("/api/v1/agents/{agent_id}/pause", response_model=ResearchProject)
def pause_agent(agent_id: str, project_id: str = "") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "paused")


@router.post("/api/v1/agents/{agent_id}/resume", response_model=ResearchProject)
def resume_agent_status(agent_id: str, project_id: str = "") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "active")


@router.post("/api/v1/agents/{agent_id}/stop", response_model=ResearchProject)
def stop_agent(agent_id: str, project_id: str = "") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "stopped")


@router.post("/api/v1/agent-runs/{run_id}/approve", response_model=ResearchProject)
def approve_agent_run(run_id: str, http_request: Request, project_id: str = "") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    run.status = "running"
    run.current_step = "approved_for_next_action"
    run.decisions.append(
        AgentDecision(
            id=new_id("decision"),
            agent_id=run.agent_id,
            run_id=run.id,
            action="approve_next_action",
            reason="Human approval recorded for supervised autonomous workflow.",
            requires_approval=True,
            approved=True,
            created_at=utc_now(),
        )
    )
    return state.store.save_project(project)


@router.get("/api/v1/agent-runs/{run_id}/status")
def agent_run_status(run_id: str, request: Request, project_id: str = "") -> dict:
    require_project_access(request, project_id, "viewer")
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {"id": run.id, "status": run.status, "current_step": run.current_step, "steps": run.steps}


@router.get("/api/v1/agent-runs/{run_id}/audit")
def agent_run_audit(run_id: str, request: Request, project_id: str = "") -> dict:
    require_project_access(request, project_id, "viewer")
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run.model_dump(mode="json")
