from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["settings"])


@router.patch("/api/v1/settings/team")
def update_team_settings(body: dict, request: Request) -> dict:
    return {"status": "updated", "team": {"id": "", "name": body.get("name", "Research Lab")}}


@router.patch("/api/v1/settings/notifications")
def update_notification_prefs(body: dict, request: Request) -> dict:
    return {"status": "saved", "preferences": body}
