from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..embeddings import rank_chunks
from ..ingestion import ingest_pdf_bytes
from ..jobs import queue_job
from ..models import PaperExtractionSet, UploadedPaper
from ._helpers import read_upload
from ._state import OBJECT_STORE, ORCHESTRATOR, STORE

logger = logging.getLogger("ai_scientist")

router = APIRouter(tags=["papers"])


@router.post("/api/projects/{project_id}/papers/upload", response_model=UploadedPaper)
async def upload_paper(project_id: str, request: Request, filename: str = "uploaded.pdf") -> UploadedPaper:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    upload_filename, content, content_type = await read_upload(request, filename)
    if not content:
        raise HTTPException(status_code=400, detail="Upload body is empty")
    logger.info("paper_ingest_started project_id=%s filename=%s content_type=%s bytes=%s", project_id, upload_filename, content_type, len(content))
    paper = ingest_pdf_bytes(
        project_id=project_id,
        filename=upload_filename,
        content=content,
        storage_dir=settings.storage_dir,
        content_type=content_type,
    )
    object_record = OBJECT_STORE.put_bytes(project_id, "pdf", upload_filename, content, content_type)
    STORE.save_object_record(object_record)
    job = queue_job("pdf_ingestion", project_id, {"paper_id": paper.id, "filename": upload_filename, "object_id": object_record.id})
    STORE.save_job(job)
    project.uploaded_papers = [item for item in project.uploaded_papers if item.id != paper.id]
    project.uploaded_papers.insert(0, paper)
    STORE.save_project(project)
    logger.info("paper_ingested project_id=%s paper_id=%s status=%s chunks=%s error=%s", project_id, paper.id, paper.status, paper.chunk_count, paper.error)
    return paper


@router.get("/api/projects/{project_id}/papers", response_model=list[UploadedPaper])
def list_papers(project_id: str, skip: int = 0, limit: int = 50) -> list[UploadedPaper]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.uploaded_papers[skip:skip + limit]


@router.get("/api/projects/{project_id}/papers/{paper_id}", response_model=UploadedPaper)
def get_paper(project_id: str, paper_id: str) -> UploadedPaper:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/api/projects/{project_id}/papers/{paper_id}/extractions", response_model=PaperExtractionSet)
def get_paper_extractions(project_id: str, paper_id: str) -> PaperExtractionSet:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper.extractions


@router.delete("/api/projects/{project_id}/papers/{paper_id}")
def delete_paper(project_id: str, paper_id: str) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.uploaded_papers = [p for p in project.uploaded_papers if p.id != paper_id]
    STORE.save_project(project)
    return {"status": "deleted", "paper_id": paper_id}


@router.get("/api/connectors/status")
def connector_status() -> list:
    return ORCHESTRATOR.search_service.connector_status()


@router.get("/api/projects/{project_id}/embedding-status")
def embedding_status(project_id: str) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    papers = project.uploaded_papers
    embedded = len([paper for paper in papers if paper.embedding_status == "embedded"])
    failed = len([paper for paper in papers if paper.embedding_status == "failed"])
    pending = len(papers) - embedded - failed
    return {
        "project_id": project_id,
        "papers": len(papers),
        "embedded": embedded,
        "pending": pending,
        "failed": failed,
        "coverage": round(embedded / max(len(papers), 1), 3),
        "items": [
            {
                "paper_id": paper.id,
                "title": paper.title,
                "embedding_status": paper.embedding_status,
                "chunks": paper.chunk_count,
                "source_type": paper.source_type,
            }
            for paper in papers
        ],
    }


@router.get("/api/projects/{project_id}/papers/{paper_id}/chunks")
def ranked_paper_chunks(project_id: str, paper_id: str, ranked_by: str | None = None, query: str = "") -> dict:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if ranked_by == "semantic" and query:
        ranking = rank_chunks(query, paper.chunks, limit=len(paper.chunks) or 8)
    else:
        ranking = []
    return {"paper_id": paper_id, "chunks": paper.chunks, "ranking": ranking}
