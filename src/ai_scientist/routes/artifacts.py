from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ._auth import require_project_access
from ._state import OBJECT_STORE, STORE

router = APIRouter(tags=["artifacts"])


@router.get("/api/v1/projects/{project_id}/artifacts")
def list_project_artifacts(project_id: str, request: Request) -> list[dict]:
    require_project_access(request, project_id, "viewer")
    return [record.model_dump(mode="json") for record in STORE.list_object_records(project_id)]


@router.get("/api/v1/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, request: Request) -> Response:
    record = STORE.get_object_record(artifact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if record.project_id:
        require_project_access(request, record.project_id, "viewer")
    content = OBJECT_STORE.read_bytes(record)
    filename = record.name or artifact_id
    return Response(
        content=content,
        media_type=record.content_type,
        headers={"content-disposition": f'attachment; filename="{Path(filename).name}"'},
    )
