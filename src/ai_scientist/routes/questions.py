from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from .. import jobs as jobs_module
from ..agents import ResearchOrchestrator
from ..ai_providers import build_provider
from ..config import settings
from ..ingestion import chunks_to_paper_sources
from ..jobs import queue_job
from ..models import (
    ResearchQuestion,
    RunQuestionRequest,
    RunQuestionResponse,
    new_id,
    utc_now,
)
from ._helpers import build_memory_from_brief
from ._state import ORCHESTRATOR, STORE

logger = logging.getLogger("ai_scientist")

router = APIRouter(tags=["questions"])


@router.post("/api/projects/{project_id}/questions/run", response_model=RunQuestionResponse)
def run_research_question(project_id: str, request: RunQuestionRequest) -> RunQuestionResponse:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    question = ResearchQuestion(id=new_id("question"), text=request.question, created_at=utc_now())
    chunks = STORE.list_document_chunks(project_id, limit=settings.max_chunks)
    extra_sources = chunks_to_paper_sources(chunks, max_chunks=settings.max_chunks)
    logger.info(
        "agent_run_started project_id=%s question_id=%s provider=%s extra_pdf_chunks=%s",
        project_id,
        question.id,
        settings.ai_provider,
        len(extra_sources),
    )
    if request.provider or request.model or request.web_search is not None or request.sources is not None:
        ai_provider = build_provider(request.provider or settings.ai_provider, request.model or settings.model)
        orchestrator = ResearchOrchestrator(ai_provider=ai_provider, web_search_enabled=request.web_search)
        run, brief = orchestrator.run(
            question,
            max_papers=request.max_papers,
            memory=project.memory if request.use_memory else [],
            extra_sources=extra_sources,
            sources=request.sources,
        )
    else:
        run, brief = ORCHESTRATOR.run(
            question,
            max_papers=request.max_papers,
            memory=project.memory if request.use_memory else [],
            extra_sources=extra_sources,
            sources=request.sources,
        )
    brief.question_id = question.id
    question.agent_run_id = run.id
    question.brief_id = brief.id

    project.questions.insert(0, question)
    project.briefs.insert(0, brief)
    project.memory = build_memory_from_brief(brief) + project.memory
    project.agent_runs = [run] + [item for item in project.agent_runs if item.id != run.id]
    STORE.save_project(project)
    STORE.save_agent_run(project_id, run)
    if run.warnings:
        logger.warning("provider_fallback project_id=%s run_id=%s warnings=%s", project_id, run.id, " | ".join(run.warnings))
    logger.info("agent_run_completed project_id=%s question_id=%s run_id=%s provider=%s", project_id, question.id, run.id, run.provider)
    return RunQuestionResponse(project=project, question=question, run=run, brief=brief)


@router.post("/api/v1/projects/{project_id}/run")
def v1_run_question(project_id: str, request: RunQuestionRequest) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job_payload = {
        "project_id": project_id,
        "question": request.question,
        "max_papers": request.max_papers,
        "use_memory": request.use_memory,
    }
    if request.sources is not None:
        job_payload["sources"] = request.sources
    if request.provider is not None:
        job_payload["provider"] = request.provider
    if request.model is not None:
        job_payload["model"] = request.model
    if request.web_search is not None:
        job_payload["web_search"] = request.web_search
    job = queue_job("research_pipeline", project_id, job_payload)

    celery_available = len(jobs_module._LOCAL_JOBS) == 0

    if not celery_available:
        jobs_module._LOCAL_JOBS.clear()
        result = jobs_module.execute_job(job.model_dump(mode="json"), job_payload)
        job.status = "completed" if result.get("status") == "completed" else "failed"
        job.result = result
        STORE.save_job(job)
        return {
            "job_id": job.id,
            "status": job.status,
            "result": result,
        }

    STORE.save_job(job)
    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Research pipeline queued. Poll GET /api/v1/jobs/{job_id} for status.",
    }


@router.get("/api/projects/{project_id}/jobs")
def list_project_jobs(project_id: str) -> list[dict]:
    return [j.model_dump(mode="json") for j in STORE.list_jobs(project_id)]
