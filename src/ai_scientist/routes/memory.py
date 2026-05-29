from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import (
    AddAnnotationRequest,
    AddMemoryRequest,
    CreateCollectionRequest,
    MemoryItem,
    PromoteMemoryRequest,
    ResearchAnnotation,
    ResearchProject,
    SourceCollection,
    new_id,
    utc_now,
)
from ._state import STORE

router = APIRouter(tags=["memory"])


@router.post("/api/projects/{project_id}/memory", response_model=ResearchProject)
def add_memory(project_id: str, request: AddMemoryRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.memory.insert(
        0,
        MemoryItem(
            id=new_id("mem"),
            kind=request.kind,
            content=request.content,
            source_ids=request.source_ids,
            tags=request.tags,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@router.post("/api/projects/{project_id}/memory/promote", response_model=ResearchProject)
def promote_memory(project_id: str, request: PromoteMemoryRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    normalized_content = request.content.strip().lower()
    existing = next(
        (
            item
            for item in project.memory
            if item.kind == request.kind and item.content.strip().lower() == normalized_content and item.status == "active"
        ),
        None,
    )
    if existing:
        existing.source_ids = sorted(set(existing.source_ids + request.source_ids))
        existing.tags = sorted(set(existing.tags + request.tags + ["promoted"]))
    else:
        project.memory.insert(
            0,
            MemoryItem(
                id=new_id("mem"),
                kind=request.kind,
                content=request.content.strip(),
                source_ids=request.source_ids,
                tags=sorted(set(request.tags + ["promoted"])),
                created_at=utc_now(),
            ),
        )
    return STORE.save_project(project)


@router.get("/api/projects/{project_id}/memory", response_model=list[MemoryItem])
def list_memory(project_id: str, kind: str | None = None, q: str | None = None, skip: int = 0, limit: int = 50) -> list[MemoryItem]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    items = project.memory
    if kind:
        items = [item for item in items if item.kind == kind]
    if q:
        query = q.lower()
        items = [
            item
            for item in items
            if query in item.content.lower() or any(query in tag.lower() for tag in item.tags)
        ]
    return items[skip:skip + limit]


@router.delete("/api/projects/{project_id}/memory/{memory_id}")
def delete_memory(project_id: str, memory_id: str) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.memory = [item for item in project.memory if item.id != memory_id]
    STORE.save_project(project)
    return {"status": "deleted", "memory_id": memory_id}


@router.post("/api/projects/{project_id}/collections", response_model=ResearchProject)
def create_collection(project_id: str, request: CreateCollectionRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.source_collections.insert(
        0,
        SourceCollection(
            id=new_id("collection"),
            name=request.name,
            description=request.description,
            source_ids=request.source_ids,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@router.post("/api/projects/{project_id}/annotations", response_model=ResearchProject)
def add_annotation(project_id: str, request: AddAnnotationRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.annotations.insert(
        0,
        ResearchAnnotation(
            id=new_id("ann"),
            target_type=request.target_type,
            target_id=request.target_id,
            note=request.note,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)
