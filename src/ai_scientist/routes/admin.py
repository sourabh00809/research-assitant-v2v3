from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..config import settings
from ..jobs import job_health
from ..object_storage import storage_health
from ..platform_db import ALEMBIC_BOOTSTRAP_SQL, database_health
from ._state import ORCHESTRATOR

router = APIRouter(tags=["admin"])


@router.get("/api/v1/admin/live")
def admin_live() -> dict:
    return {"status": "live", "product": "Research Assistant"}


@router.get("/api/v1/admin/ready")
def admin_ready() -> dict:
    health = admin_health()
    required = [health["database"], health["redis_workers"], health["storage"]]
    ready = all(item.get("status") in {"ready", "local-fallback", "fallback"} for item in required)
    if settings.production:
        ready = all(item.get("status") == "ready" for item in required)
    if not ready:
        raise HTTPException(status_code=503, detail=health)
    return {"status": "ready", "checks": health}


@router.get("/api/v1/admin/migrations/bootstrap.sql", response_class=PlainTextResponse)
def migration_bootstrap_sql() -> str:
    return ALEMBIC_BOOTSTRAP_SQL


@router.get("/api/v1/admin/health")
def admin_health() -> dict:
    return {
        "database": database_health(),
        "redis_workers": job_health(),
        "storage": storage_health(),
        "sandbox": {"backend": settings.sandbox_backend, "image": settings.sandbox_image},
        "connectors": [item.model_dump(mode="json") for item in ORCHESTRATOR.search_service.connector_status()],
        "billing": {"tier": "free", "status": "dev_mode"},
    }
