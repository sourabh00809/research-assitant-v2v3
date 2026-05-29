from __future__ import annotations

from email import policy
from email.parser import BytesParser
from typing import Any

from fastapi import Request

from ..models import ExperimentPlan, MemoryItem, ResearchBrief, utc_now
from ._state import state


def resolve_brief(project: Any, brief_id: str | None = None, question_id: str | None = None) -> ResearchBrief | None:
    pid = project.id if hasattr(project, "id") else project["id"]
    briefs = project.briefs if hasattr(project, "briefs") else project.get("briefs") or []
    if brief_id:
        return state.store.get_brief(pid, brief_id)
    if question_id:
        for b in (briefs or []):
            qid = b.question_id if hasattr(b, "question_id") else b.get("question_id")
            bid = b.id if hasattr(b, "id") else b["id"]
            if qid == question_id:
                return state.store.get_brief(pid, bid)
    if briefs:
        bid = briefs[0].id if hasattr(briefs[0], "id") else briefs[0]["id"]
        return state.store.get_brief(pid, bid)
    return None


def resolve_experiment_plan(project: Any, plan_id: str | None = None) -> ExperimentPlan | None:
    pid = project.id if hasattr(project, "id") else project["id"]
    plans = project.experiment_plans if hasattr(project, "experiment_plans") else project.get("experiment_plans") or []
    if plan_id:
        return state.store.get_experiment_plan(pid, plan_id)
    if plans:
        eid = plans[0].id if hasattr(plans[0], "id") else plans[0]["id"]
        return state.store.get_experiment_plan(pid, eid)
    return None


def build_memory_from_brief(brief: ResearchBrief | None) -> list[MemoryItem]:
    if not brief:
        return []
    items = []
    for ev in (brief.evidence_items or []):
        items.append(MemoryItem(
            id=ev.id,
            kind="evidence",
            content=ev.claim[:512] if ev.claim else "",
            tags=[ev.extraction_type] if ev.extraction_type else [],
            source_ids=[ev.source_id] if ev.source_id else [],
            created_at=utc_now(),
        ))
    return items


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


async def read_upload(request: Request, fallback_filename: str) -> tuple[str, bytes, str]:
    content_type = request.headers.get("content-type", "application/pdf")
    body = await request.body()
    if not content_type.lower().startswith("multipart/form-data"):
        return fallback_filename, body, content_type
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        payload = part.get_payload(decode=True) or b""
        part_filename = part.get_filename()
        if part_filename or part.get_param("name", header="content-disposition") in {"file", "paper", "upload"}:
            return part_filename or fallback_filename, payload, part.get_content_type() or "application/pdf"
    return fallback_filename, b"", content_type
