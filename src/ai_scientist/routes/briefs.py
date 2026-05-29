from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from ..export import brief_to_markdown
from ..models import (
    EvidenceFeedbackRequest,
    EvidenceQualityReport,
    ResearchAnnotation,
    ResearchProject,
    new_id,
    utc_now,
)
from ._helpers import escape_xml
from ._state import state

router = APIRouter(tags=["briefs"])


@router.get("/api/projects/{project_id}/briefs/{brief_id}")
def get_brief(project_id: str, brief_id: str):
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = next((item for item in project.briefs if item.id == brief_id), None)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@router.get("/api/projects/{project_id}/briefs/{brief_id}/quality", response_model=EvidenceQualityReport)
def get_brief_quality(project_id: str, brief_id: str) -> EvidenceQualityReport:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = next((item for item in project.briefs if item.id == brief_id), None)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.quality_report:
        return brief.quality_report
    if brief.quality_report_id:
        report = state.store.get_quality_report(project_id, brief.quality_report_id)
        if report:
            return report
    report = next((item for item in project.quality_reports if item.brief_id == brief_id), None)
    if report:
        return report
    raise HTTPException(status_code=404, detail="Quality report not found")


@router.get("/api/projects/{project_id}/briefs/{brief_id}/export.md", response_class=PlainTextResponse)
def export_brief(project_id: str, brief_id: str) -> PlainTextResponse:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = next((item for item in project.briefs if item.id == brief_id), None)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return PlainTextResponse(
        brief_to_markdown(brief),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{brief.id}.md"'},
    )


@router.get("/api/projects/{project_id}/briefs/{brief_id}/export.pdf")
def export_brief_pdf(project_id: str, brief_id: str) -> Response:
    markdown = export_brief(project_id, brief_id).body.decode("utf-8")
    try:
        from weasyprint import HTML

        pdf = HTML(string=f"<pre>{escape_xml(markdown)}</pre>").write_pdf()
        return Response(pdf, media_type="application/pdf")
    except Exception:
        return PlainTextResponse(
            "PDF export fallback: install WeasyPrint to render PDF.\n\n" + markdown,
            media_type="text/plain",
        )


@router.get("/api/projects/{project_id}/briefs/{brief_id}/export.tex", response_class=PlainTextResponse)
def export_brief_tex(project_id: str, brief_id: str) -> PlainTextResponse:
    markdown = export_brief(project_id, brief_id).body.decode("utf-8")
    tex = "\\section*{Research Brief}\n\\begin{verbatim}\n" + markdown + "\\end{verbatim}\n"
    return PlainTextResponse(tex, media_type="application/x-tex")


@router.delete("/api/projects/{project_id}/briefs/{brief_id}")
def delete_brief(project_id: str, brief_id: str) -> dict:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.briefs = [b for b in project.briefs if b.id != brief_id]
    state.store.save_project(project)
    return {"status": "deleted", "brief_id": brief_id}


@router.delete("/api/projects/{project_id}/questions/{question_id}")
def delete_question(project_id: str, question_id: str) -> dict:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.questions = [q for q in project.questions if q.id != question_id]
    state.store.save_project(project)
    return {"status": "deleted", "question_id": question_id}


@router.get("/api/projects/{project_id}/runs/{run_id}/events")
def run_events(project_id: str, run_id: str) -> StreamingResponse:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    def stream():
        for step in run.steps:
            yield f"event: step\ndata: {step.model_dump_json()}\n\n"
        yield f"event: completed\ndata: {run.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.patch("/api/projects/{project_id}/evidence/{evidence_id}/feedback", response_model=ResearchProject)
def evidence_feedback(project_id: str, evidence_id: str, request: EvidenceFeedbackRequest) -> ResearchProject:
    project = state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.annotations.insert(
        0,
        ResearchAnnotation(
            id=new_id("ann"),
            target_type="brief",
            target_id=evidence_id,
            note=f"Evidence feedback: {request.rating}. {request.note}".strip(),
            created_at=utc_now(),
        ),
    )
    return state.store.save_project(project)
