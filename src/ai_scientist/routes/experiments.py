from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..experiment import generate_script, list_templates, recommend_experiment_plan
from ..experiments import create_experiment_plan
from ..export import experiment_plan_to_markdown
from ..jobs import queue_job
from ..models import (
    CreateExperimentPlanRequest,
    CreateResearchTaskRequest,
    ExperimentPlan,
    GenerateScriptRequest,
    RecommendExperimentPlanRequest,
    ResearchProject,
    ResearchTask,
    UpdateExperimentPlanRequest,
    new_id,
    utc_now,
)
from ._helpers import resolve_brief
from ._state import OBJECT_STORE, STORE

router = APIRouter(tags=["experiments"])


@router.post("/api/projects/{project_id}/experiment-plans", response_model=ResearchProject)
def create_plan(project_id: str, request: CreateExperimentPlanRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    brief = resolve_brief(project, request.brief_id, request.question_id)
    plan = create_experiment_plan(
        brief,
        objective=request.objective,
        memory=project.memory,
        hypothesis_id=request.hypothesis_id,
        template_id=request.template_id,
        status=request.status,
    )
    project.experiment_plans.insert(0, plan)
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind="experiment_plan",
            status="completed",
            title=plan.title,
            summary="Generated datasets, baselines, metrics, ablations, validation protocol, and implementation scaffold.",
            target_id=plan.id,
            created_at=utc_now(),
            completed_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@router.get("/api/experiment-templates")
def experiment_templates() -> list[dict]:
    return list_templates()


@router.post("/api/projects/{project_id}/experiment-plans/recommend")
def recommend_plan(project_id: str, request: RecommendExperimentPlanRequest) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = resolve_brief(project, request.brief_id, None) if request.brief_id or project.briefs else None
    question = request.question or (brief.title if brief else "")
    return recommend_experiment_plan(brief, question=question, domain=request.domain, task=request.task, top_k=request.top_k)


@router.patch("/api/projects/{project_id}/experiment-plans/{plan_id}", response_model=ExperimentPlan)
def update_plan(project_id: str, plan_id: str, request: UpdateExperimentPlanRequest) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(plan, field, value)
    STORE.save_project(project)
    return plan


@router.post("/api/projects/{project_id}/experiment-plans/{plan_id}/generate-script", response_model=ExperimentPlan)
def generate_plan_script(project_id: str, plan_id: str, request: GenerateScriptRequest | None = None) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    if request:
        if request.validation_tests:
            plan.validation_plan.statistical_tests = request.validation_tests
        if request.confidence_interval:
            plan.validation_plan.confidence_interval = request.confidence_interval
        if request.correction:
            plan.validation_plan.correction = request.correction
    plan.generated_script = generate_script(plan)
    plan.implementation_template = plan.generated_script
    object_record = OBJECT_STORE.put_bytes(project_id, "script", f"{plan.id}.py", plan.generated_script.encode("utf-8"), "text/x-python")
    STORE.save_object_record(object_record)
    job = queue_job("script_generation", project_id, {"plan_id": plan.id, "object_id": object_record.id})
    STORE.save_job(job)
    STORE.save_project(project)
    return plan


@router.get("/api/projects/{project_id}/experiment-plans/{plan_id}/script.py", response_class=PlainTextResponse)
def get_plan_script(project_id: str, plan_id: str) -> PlainTextResponse:
    plan = get_plan(project_id, plan_id)
    script = plan.generated_script or generate_script(plan)
    return PlainTextResponse(
        script,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{plan.id}.py"'},
    )


@router.delete("/api/projects/{project_id}/experiment-plans/{plan_id}")
def delete_experiment_plan(project_id: str, plan_id: str) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.experiment_plans = [p for p in project.experiment_plans if p.id != plan_id]
    STORE.save_project(project)
    return {"status": "deleted", "plan_id": plan_id}


@router.get("/api/projects/{project_id}/experiment-plans/{plan_id}", response_model=ExperimentPlan)
def get_plan(project_id: str, plan_id: str) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    return plan


@router.get("/api/projects/{project_id}/experiment-plans/{plan_id}/export.md", response_class=PlainTextResponse)
def export_plan(project_id: str, plan_id: str) -> PlainTextResponse:
    plan = get_plan(project_id, plan_id)
    return PlainTextResponse(
        experiment_plan_to_markdown(plan),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{plan.id}.md"'},
    )


@router.post("/api/projects/{project_id}/tasks", response_model=ResearchProject)
def create_task(project_id: str, request: CreateResearchTaskRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind=request.kind,
            status="queued",
            title=request.title,
            summary=request.summary,
            target_id=request.target_id,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)
