from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..hypotheses import generate_hypotheses
from ..models import (
    GenerateHypothesesRequest,
    HypothesisCandidate,
    ResearchProject,
    ResearchTask,
    new_id,
    utc_now,
)
from ._helpers import resolve_brief, resolve_experiment_plan
from ._state import STORE

router = APIRouter(tags=["hypotheses"])


@router.post("/api/projects/{project_id}/hypotheses", response_model=ResearchProject)
def create_hypotheses(project_id: str, request: GenerateHypothesesRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    brief = resolve_brief(project, request.brief_id, None)
    experiment_plan = resolve_experiment_plan(project, request.experiment_plan_id)
    hypotheses = generate_hypotheses(
        brief,
        memory=project.memory,
        experiment_plan=experiment_plan,
        max_hypotheses=request.max_hypotheses,
    )
    project.hypotheses = hypotheses + project.hypotheses
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind="hypothesis_generation",
            status="completed",
            title=f"Generated {len(hypotheses)} hypotheses",
            summary="Created grounded hypothesis candidates from evidence, methodology gaps, memory, and experiment plans.",
            target_id=hypotheses[0].id if hypotheses else None,
            created_at=utc_now(),
            completed_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@router.get("/api/projects/{project_id}/hypotheses", response_model=list[HypothesisCandidate])
def list_hypotheses(project_id: str) -> list[HypothesisCandidate]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.hypotheses
