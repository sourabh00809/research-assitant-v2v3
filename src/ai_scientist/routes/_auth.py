from __future__ import annotations

import re

from fastapi import HTTPException, Request

from ..config import settings
from ..rbac import require_role
from ._state import state

_API_PROJECT_PATH = re.compile(r"^/api/(v\d/)?projects/(?P<project_id>[^/]+)(?:/|$)")


def current_clerk_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ")
    if state.clerk_verifier:
        return state.clerk_verifier.verify(token)
    return None


def require_project_access(request: Request, project_id: str, minimum_role: str = "viewer") -> None:
    if settings.disable_auth:
        return
    clerk_user = current_clerk_user(request)
    if not clerk_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    require_role(clerk_user.role, minimum_role)


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware that protects all project-scoped API routes."""
    if settings.disable_auth:
        return await call_next(request)
    match = _API_PROJECT_PATH.match(request.url.path)
    if match:
        try:
            require_project_access(request, match.group("project_id"))
        except HTTPException as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)
