from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..models import CreateProjectRequest, ResearchProject, new_id, utc_now
from ._state import STORE

router = APIRouter(tags=["projects"])


@router.get("/api/projects", response_model=list[ResearchProject])
def list_projects() -> list[ResearchProject]:
    return STORE.list_projects()


@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict:
    if not STORE.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    STORE.delete_project(project_id)
    return {"status": "deleted", "project_id": project_id}


@router.post("/api/projects", response_model=ResearchProject)
def create_project(request: CreateProjectRequest) -> ResearchProject:
    project = ResearchProject(
        id=new_id("project"),
        name=request.name,
        description=request.description,
        created_at=utc_now(),
    )
    return STORE.save_project(project)


@router.get("/api/v1/projects", response_model=list[ResearchProject])
def list_projects_v1(request: Request, skip: int = 0, limit: int = 50) -> list[ResearchProject]:
    return list_projects()[skip:skip + limit]


@router.post("/api/v1/projects", response_model=ResearchProject)
def create_project_v1(request: CreateProjectRequest, http_request: Request) -> ResearchProject:
    return create_project(request)


@router.get("/api/projects/{project_id}", response_model=ResearchProject)
def get_project(project_id: str) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
