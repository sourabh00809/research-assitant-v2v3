from __future__ import annotations

from collections import deque
from typing import Any

from .config import settings
from .models import JobRecord, new_id, utc_now


_LOCAL_JOBS: deque[JobRecord] = deque()


def queue_job(kind: str, project_id: str | None = None, payload: dict[str, Any] | None = None) -> JobRecord:
    job = JobRecord(
        id=new_id("job"),
        project_id=project_id,
        kind=kind,  # type: ignore[arg-type]
        status="queued",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    try:
        from celery import Celery  # type: ignore

        app = Celery("ai_scientist", broker=settings.redis_url, backend=settings.redis_url)
        app.send_task("ai_scientist.jobs.execute_job", args=[job.model_dump(mode="json"), payload or {}])
        return job
    except Exception:
        _LOCAL_JOBS.appendleft(job)
        return job


def execute_job(job_payload: dict, payload: dict | None = None) -> dict:
    job = JobRecord.model_validate(job_payload)
    job.status = "running"
    job.attempts += 1
    job.updated_at = utc_now()
    try:
        from .store_factory import build_store

        build_store().save_job(job)
    except Exception:
        pass
    job.status = "completed"
    job.updated_at = utc_now()
    try:
        from .store_factory import build_store

        build_store().save_job(job)
    except Exception:
        pass
    return {"job": job.model_dump(mode="json"), "payload": payload or {}}


def job_health() -> dict:
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(settings.redis_url)
        client.ping()
        return {"backend": "celery-redis", "status": "ready", "queued_local": len(_LOCAL_JOBS)}
    except Exception as exc:
        return {"backend": "local-inline", "status": "fallback", "queued_local": len(_LOCAL_JOBS), "error": str(exc)}
