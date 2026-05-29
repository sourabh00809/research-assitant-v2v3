from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..jobs import job_health, queue_job
from ..models import QueueJobRequest
from ._state import STORE

router = APIRouter(tags=["jobs"])


@router.post("/api/v1/jobs")
def enqueue_job(request: QueueJobRequest) -> dict:
    job = queue_job(request.kind, request.project_id, request.payload)
    STORE.save_job(job)
    return job.model_dump(mode="json")


@router.get("/api/v1/jobs/health")
def jobs_health() -> dict:
    return job_health()


@router.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = STORE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump(mode="json")
