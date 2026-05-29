from __future__ import annotations

from email import policy
from email.parser import BytesParser

from fastapi import HTTPException, Request

from ..models import ExperimentPlan, MemoryItem, ResearchBrief, utc_now


def resolve_brief(project, brief_id: str | None = None, question_id: str | None = None) -> ResearchBrief:
    if brief_id:
        brief = next((item for item in project.briefs if item.id == brief_id), None)
        if not brief:
            raise HTTPException(status_code=404, detail="Brief not found")
        return brief
    if question_id:
        brief = next((item for item in project.briefs if item.question_id == question_id), None)
        if not brief:
            raise HTTPException(status_code=404, detail="Brief for question not found")
        return brief
    if project.briefs:
        return project.briefs[0]
    raise HTTPException(status_code=400, detail="Create a research brief before generating an experiment plan")


def resolve_experiment_plan(project, plan_id: str | None = None) -> ExperimentPlan | None:
    if plan_id:
        plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
        if not plan:
            raise HTTPException(status_code=404, detail="Experiment plan not found")
        return plan
    return project.experiment_plans[0] if project.experiment_plans else None


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
