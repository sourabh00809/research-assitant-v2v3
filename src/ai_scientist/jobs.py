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
        kind=kind,
        status="queued",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    try:
        from celery import Celery

        app = Celery("ai_scientist", broker=settings.redis_url, backend=settings.redis_url)
        app.send_task("ai_scientist.jobs.execute_job", args=[job.model_dump(mode="json"), payload or {}])
        return job
    except Exception:
        _LOCAL_JOBS.appendleft(job)
        return job


def dispatch_job(kind: str, job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "research_pipeline":
        return _run_research_pipeline(job, payload)
    if kind == "pdf_ingestion":
        return _run_pdf_ingestion(job, payload)
    if kind == "agent_workflow":
        return _run_agent_workflow(job, payload)
    if kind == "connector_search":
        return _run_connector_search(job, payload)
    if kind == "embedding_update":
        return _run_embedding_update(job, payload)
    if kind == "script_generation":
        return _run_script_generation(job, payload)
    if kind == "export_generation":
        return _run_export_generation(job, payload)
    return {"status": "unknown_kind", "kind": kind}


def _save_job_status(job: JobRecord) -> None:
    try:
        from .store_factory import build_store

        build_store().save_job(job)
    except Exception:
        pass


def _build_memory_from_brief(brief) -> list:
    from .models import MemoryItem, new_id, utc_now

    items: list = []
    for content in brief.open_problems[:2]:
        items.append(MemoryItem(id=new_id("mem"), kind="gap", content=content, tags=["auto", "open-problem"], created_at=utc_now()))
    for content in brief.suggested_next_directions[:2]:
        items.append(MemoryItem(id=new_id("mem"), kind="idea", content=content, tags=["auto", "next-direction"], created_at=utc_now()))
    return items


def _run_research_pipeline(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .agents import ResearchOrchestrator
        from .ai_providers import build_provider
        from .ingestion import chunks_to_paper_sources
        from .models import ResearchQuestion
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        question_text = payload.get("question", "")
        max_papers = payload.get("max_papers", 6)
        use_memory = payload.get("use_memory", True)

        project = store.get_project(project_id)
        if not project:
            return {"status": "failed", "error": "project_not_found"}

        question = ResearchQuestion(id=new_id("question"), text=question_text, created_at=utc_now())
        chunks = store.list_document_chunks(project_id, limit=settings.max_chunks)
        extra_sources = chunks_to_paper_sources(chunks, max_chunks=settings.max_chunks)

        orchestrator = ResearchOrchestrator(ai_provider=build_provider(settings.ai_provider, settings.model))
        run, brief = orchestrator.run(
            question,
            max_papers=max_papers,
            memory=project.memory if use_memory else [],
            extra_sources=extra_sources,
        )
        brief.question_id = question.id
        question.agent_run_id = run.id
        question.brief_id = brief.id

        project.questions.insert(0, question)
        project.briefs.insert(0, brief)
        project.memory = _build_memory_from_brief(brief) + project.memory
        project.agent_runs = [run] + [item for item in project.agent_runs if item.id != run.id]
        store.save_project(project)
        store.save_agent_run(project_id, run)

        return {
            "status": "completed",
            "question_id": question.id,
            "run_id": run.id,
            "brief_id": brief.id,
            "evidence_count": len(brief.evidence_items),
        }
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_pdf_ingestion(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        paper_id = payload.get("paper_id", "")

        project = store.get_project(project_id)
        if not project:
            return {"status": "failed", "error": "project_not_found"}

        paper = next((p for p in project.uploaded_papers if p.id == paper_id), None)
        if not paper:
            return {"status": "failed", "error": "paper_not_found"}

        if paper.status == "processed":
            return {"status": "completed", "paper_id": paper_id, "message": "already_processed", "chunks": paper.chunk_count}

        from pathlib import Path

        from .config import settings
        from .ingestion import ingest_pdf_bytes

        storage_path = Path(paper.storage_path)
        if not storage_path.exists():
            storage_path = settings.storage_dir / project_id / storage_path.name
        if storage_path.exists():
            content = storage_path.read_bytes()
            updated = ingest_pdf_bytes(project_id, paper.filename, content, settings.storage_dir)
            paper.page_count = updated.page_count
            paper.chunk_count = updated.chunk_count
            paper.status = updated.status
            paper.chunks = updated.chunks
            paper.ingestion_runs = updated.ingestion_runs
            paper.extractions = updated.extractions
            paper.error = updated.error
            paper.embedding_status = updated.embedding_status
            for i, p in enumerate(project.uploaded_papers):
                if p.id == paper_id:
                    project.uploaded_papers[i] = paper
                    break
            store.save_project(project)

        return {"status": "completed", "paper_id": paper_id, "chunks": paper.chunk_count}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_agent_workflow(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .autonomous import complete_literature_monitor, literature_monitor_step
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        agent_id = payload.get("agent_id", "")
        run_id = payload.get("run_id", "")

        project = store.get_project(project_id) if project_id else None
        if not project:
            return {"status": "failed", "error": "project_not_found"}

        agent_run = next((r for r in project.autonomous_agent_runs if r.id == run_id), None)
        saved_search = project.saved_searches[0] if project.saved_searches else None
        if not agent_run:
            return {"status": "failed", "error": "run_not_found"}

        literature_monitor_step(project, agent_run, (saved_search.query if saved_search else agent_id))
        complete_literature_monitor(project, agent_run, saved_search)
        store.save_project(project)

        return {"status": "completed", "agent_id": agent_id, "run_id": run_id}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_connector_search(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .retrieval import SearchService

        query = payload.get("query", "")
        max_results = payload.get("max_results", 6)
        service = SearchService()
        papers = service.search(query, max_papers=max_results)
        return {"status": "completed", "results": len(papers), "source_ids": [p.id for p in papers]}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_embedding_update(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .embeddings import EmbeddingService
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        paper_id = payload.get("paper_id", "")

        project = store.get_project(project_id)
        if not project:
            return {"status": "failed", "error": "project_not_found"}

        emb = EmbeddingService()
        updated_count = 0
        for paper in project.uploaded_papers:
            if paper_id and paper.id != paper_id:
                continue
            if paper.embedding_status == "embedded":
                updated_count += 1
                continue
            for chunk in paper.chunks:
                emb.record("chunk", chunk.id, chunk.text)
            paper.embedding_status = "embedded"
            updated_count += 1

        store.save_project(project)
        return {"status": "completed", "papers_updated": updated_count}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_script_generation(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .experiment.scripts import generate_script
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        plan_id = payload.get("plan_id", "")

        project = store.get_project(project_id)
        if not project:
            return {"status": "failed", "error": "project_not_found"}

        plan = next((p for p in project.experiment_plans if p.id == plan_id), None)
        if not plan:
            return {"status": "failed", "error": "plan_not_found"}

        if not plan.generated_script:
            plan.generated_script = generate_script(plan)
            plan.implementation_template = plan.generated_script
            for i, p in enumerate(project.experiment_plans):
                if p.id == plan_id:
                    project.experiment_plans[i] = plan
                    break
            store.save_project(project)

        return {"status": "completed", "plan_id": plan_id, "script_length": len(plan.generated_script)}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _run_export_generation(job: JobRecord, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from .export import brief_to_markdown
        from .store_factory import build_store

        store = build_store()
        project_id = payload.get("project_id", job.project_id or "")
        brief_id = payload.get("brief_id", "")
        project = store.get_project(project_id) if project_id else None
        if not project:
            return {"status": "failed", "error": "project_not_found"}
        brief = next((b for b in project.briefs if b.id == brief_id), None)
        if not brief:
            return {"status": "failed", "error": "brief_not_found"}
        markdown = brief_to_markdown(brief)
        return {"status": "completed", "brief_id": brief_id, "markdown_length": len(markdown)}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def execute_job(job_payload: dict, payload: dict | None = None) -> dict:
    job = JobRecord.model_validate(job_payload)
    job.status = "running"
    job.attempts += 1
    job.updated_at = utc_now()
    _save_job_status(job)

    result = dispatch_job(job.kind, job, payload or {})

    job.status = "completed" if result.get("status") == "completed" else "failed"
    job.result = result
    if result.get("error"):
        job.error = result["error"]
    job.updated_at = utc_now()
    _save_job_status(job)

    return result


def job_health() -> dict:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url)
        client.ping()
        return {"backend": "celery-redis", "status": "ready", "queued_local": len(_LOCAL_JOBS)}
    except Exception as exc:
        return {"backend": "local-inline", "status": "fallback", "queued_local": len(_LOCAL_JOBS), "error": str(exc)}
