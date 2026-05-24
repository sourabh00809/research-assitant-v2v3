from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs
from email import policy
from email.parser import BytesParser
<<<<<<< HEAD
from time import perf_counter
from uuid import uuid4
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44

from fastapi import FastAPI, HTTPException, Request, Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
=======
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
from fastapi.staticfiles import StaticFiles

from .agents import ResearchOrchestrator
from .autonomous import (
    complete_literature_monitor,
    create_saved_search as create_saved_search_record,
    literature_monitor_step,
    record_execution_artifact,
    request_experiment_approval,
    start_agent_run,
)
from .ai_providers import build_provider
from .auth import COOKIE_NAME, JWT_COOKIE_NAME, PasswordGateMiddleware, decode_jwt, login_page, make_jwt, make_session, password_hash, verify_password
from .billing import apply_webhook, create_checkout_session, create_portal_session, verify_webhook_signature
from .config import settings
from .experiments import create_experiment_plan
from .export import brief_to_markdown, experiment_plan_to_markdown
from .experiment import generate_script, list_templates, recommend_experiment_plan
from .graph import build_research_graph
from .hypotheses import generate_hypotheses
from .ingestion import chunks_to_paper_sources, ingest_pdf_bytes
from .embeddings import rank_chunks
from .jobs import job_health, queue_job
from .object_storage import ObjectStore, storage_health
from .platform_db import ALEMBIC_BOOTSTRAP_SQL, database_health
from .rate_limit import check_rate_limit
from .rbac import require_role
from .saas import create_single_user_tenant, create_team_membership, usage_allowed, usage_summary
from .sandbox import run_sandbox
from .models import (
    AddMemoryRequest,
    AddAnnotationRequest,
    BootstrapTenantRequest,
    BillingCheckoutRequest,
    BillingWebhookRequest,
    CreateCollectionRequest,
    CreateExperimentPlanRequest,
    CreateProjectRequest,
    CreateResearchTaskRequest,
    CreateAgentRequest,
    CreateSavedSearchRequest,
    EvidenceFeedbackRequest,
    ExperimentPlan,
    GenerateScriptRequest,
    GenerateHypothesesRequest,
    HypothesisCandidate,
    MemoryItem,
    PaperExtractionSet,
<<<<<<< HEAD
    LoginRequest,
    QueueJobRequest,
    PromoteMemoryRequest,
    RecordUsageRequest,
    RecommendExperimentPlanRequest,
    UpdateExperimentPlanRequest,
    AgentDefinition,
    AgentDecision,
    AgentRunRecord,
=======
    PromoteMemoryRequest,
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
    ResearchAnnotation,
    EvidenceQualityReport,
    ResearchProject,
    ResearchQuestion,
    ResearchTask,
    ResearchGraph,
    RunQuestionRequest,
    RunQuestionResponse,
    RunAgentStepRequest,
    SandboxRunRequest,
    SignupRequest,
    SourceCollection,
    UsageEvent,
    UploadedPaper,
    new_id,
    utc_now,
)
<<<<<<< HEAD
from .store_factory import build_store
=======
from .storage import SQLiteStore
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44

logger = logging.getLogger("ai_scientist")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

BASE_DIR = Path(__file__).resolve().parents[2]
<<<<<<< HEAD
STORE = build_store()
=======
STORE = SQLiteStore(settings.db_path)
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
ORCHESTRATOR = ResearchOrchestrator(ai_provider=build_provider(settings.ai_provider, settings.model))
STATIC_DIR = Path(__file__).resolve().parent / "static"
OBJECT_STORE = ObjectStore()

app = FastAPI(
    title="AI Scientist Platform",
    description="Citation-grounded research intelligence workspace.",
    version="0.1.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PasswordGateMiddleware, password=settings.app_password)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


<<<<<<< HEAD
@app.middleware("http")
async def request_context_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
def validate_production_configuration() -> None:
    if not settings.production:
        return
    weak_values = {"", "change-me", "change-this-local-secret", "dev-change-me"}
    failures = []
    if settings.resolved_store_backend != "postgres" or not settings.database_url:
        failures.append("DATABASE_URL/Postgres store is required")
    if settings.jwt_secret in weak_values or len(settings.jwt_secret) < 32:
        failures.append("AI_SCIENTIST_JWT_SECRET must be a strong secret")
    if settings.app_password in weak_values or len(settings.app_password) < 12:
        failures.append("AI_SCIENTIST_APP_PASSWORD must be set")
    if not settings.cookie_secure:
        failures.append("AI_SCIENTIST_COOKIE_SECURE=true is required")
    if settings.storage_backend != "minio":
        failures.append("AI_SCIENTIST_STORAGE_BACKEND=minio is required")
    if failures:
        raise RuntimeError("Production configuration is unsafe: " + "; ".join(failures))


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("api_error path=%s method=%s error=%s", request.url.path, request.method, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse("/app", status_code=307)


@app.get("/legacy")
def legacy_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/app")
def next_app_placeholder() -> HTMLResponse:
    path = BASE_DIR / "frontend" / "out" / "index.html"
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse(v2_v3_workspace_html())


@app.get("/login")
def login() -> HTMLResponse:
    return login_page()


@app.post("/api/login")
async def login_submit(request: Request):
    body = (await request.body()).decode("utf-8", errors="ignore")
    password = parse_qs(body).get("password", [""])[0]
    if not settings.app_password or password == settings.app_password:
        secret = hashlib.sha256(settings.app_password.encode("utf-8")).hexdigest()
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(COOKIE_NAME, make_session(secret), httponly=True, samesite="lax")
        return response
    return login_page("Incorrect password")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "AI Scientist Platform",
        "mode": "research-intelligence-beta",
        "storage": "sqlite",
        "ai_provider": settings.ai_provider,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "api_versions": ["legacy", "v1"],
    }


@app.get("/api/v1/health")
def versioned_health() -> dict:
    return health()


@app.post("/api/v1/auth/signup")
def signup(request: SignupRequest, response: FastAPIResponse) -> dict:
    existing = STORE.get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user, team, subscription = create_single_user_tenant(
        email=request.email.strip().lower(),
        team_name=request.team_name,
        tier="free",
    )
    user.provider = "password"
    user.password_hash = password_hash(request.password)
    membership = create_team_membership(user, team)
    STORE.save_tenant_bundle(user, team, membership, subscription)
    token = make_jwt({"sub": user.id, "team_id": team.id, "role": membership.role}, settings.jwt_secret, settings.jwt_ttl_seconds)
    response.set_cookie(JWT_COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    return {"user": user.model_dump(mode="json"), "team": team.model_dump(mode="json"), "role": membership.role}


@app.post("/api/v1/auth/login")
def login_v1(request: LoginRequest, response: FastAPIResponse) -> dict:
    user = STORE.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    membership = (STORE.list_team_memberships(user_id=user.id) or [None])[0]
    if not membership:
        raise HTTPException(status_code=403, detail="User has no team membership")
    team = STORE.get_team(membership.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    token = make_jwt({"sub": user.id, "team_id": team.id, "role": membership.role}, settings.jwt_secret, settings.jwt_ttl_seconds)
    response.set_cookie(JWT_COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    return {"user": user.model_dump(mode="json"), "team": team.model_dump(mode="json"), "role": membership.role}


@app.post("/api/v1/auth/logout")
def logout_v1(response: FastAPIResponse) -> dict:
    response.delete_cookie(JWT_COOKIE_NAME)
    return {"status": "ok"}


@app.get("/api/v1/auth/session")
def auth_session(request: Request) -> dict:
    claims = decode_jwt(request.cookies.get(JWT_COOKIE_NAME, ""), settings.jwt_secret)
    if not claims:
        return {"authenticated": False}
    user = STORE.get_user(claims.user_id)
    team = STORE.get_team(claims.team_id)
    return {
        "authenticated": bool(user and team),
        "user": user.model_dump(mode="json") if user else None,
        "team": team.model_dump(mode="json") if team else None,
        "role": claims.role,
    }


def current_claims(request: Request):
    return decode_jwt(request.cookies.get(JWT_COOKIE_NAME, ""), settings.jwt_secret)


def require_claims(request: Request):
    claims = current_claims(request)
    if not claims:
        raise HTTPException(status_code=401, detail="Authentication required")
    return claims


def require_project_access(request: Request, project_id: str, minimum_role: str = "viewer") -> None:
    claims = current_claims(request)
    if not claims:
        if settings.production:
            raise HTTPException(status_code=401, detail="Authentication required")
        return
    require_role(claims.role, minimum_role)
    project = STORE.get_project(project_id)
    if project and project.team_id and project.team_id != claims.team_id:
        raise HTTPException(status_code=403, detail="Project is outside this team")


@app.post("/api/v1/tenancy/bootstrap")
def bootstrap_tenant(request: BootstrapTenantRequest) -> dict:
    user, team, subscription = create_single_user_tenant(
        email=request.email,
        team_name=request.team_name,
        tier=request.tier,
    )
    membership = create_team_membership(user, team)
    STORE.save_tenant_bundle(user, team, membership, subscription)
    return {
        "user": user.model_dump(mode="json"),
        "team": team.model_dump(mode="json"),
        "membership": membership.model_dump(mode="json"),
        "subscription": subscription.model_dump(mode="json"),
    }


@app.post("/api/v1/usage")
def record_usage(request: RecordUsageRequest) -> dict:
    event = STORE.record_usage_event(
        UsageEvent(
            id=new_id("usage"),
            subject_id=request.subject_id,
            kind=request.kind,
            quantity=request.quantity,
            metadata=request.metadata,
            created_at=utc_now(),
        )
    )
    return event.model_dump(mode="json")


@app.get("/api/v1/usage/limits")
def get_usage_limits(subject_id: str, team_id: str | None = None) -> dict:
    events = STORE.list_usage_events(subject_id)
    subscriptions = STORE.list_subscriptions(team_id)
    subscription = subscriptions[0] if subscriptions else None
    if not subscription:
        _, team, subscription = create_single_user_tenant(team_name="Local Workspace")
    return usage_summary(subscription, events)


@app.get("/api/v1/rate-limit")
def rate_limit_status(key: str = "default") -> dict:
    result = check_rate_limit(key)
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result)
    return result


@app.post("/api/v1/billing/checkout")
def billing_checkout(request: BillingCheckoutRequest) -> dict:
    return create_checkout_session(request.team_id, request.tier, request.success_url, request.cancel_url)


@app.post("/api/v1/billing/portal")
def billing_portal(team_id: str, return_url: str = "http://127.0.0.1:8000/app") -> dict:
    return create_portal_session(team_id, return_url)


@app.post("/api/v1/billing/webhook")
async def billing_webhook(request: Request) -> dict:
    body = await request.body()
    if not verify_webhook_signature(body, request.headers.get("stripe-signature", "")):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    event = json.loads(body.decode("utf-8") or "{}")
    team_id = event.get("data", {}).get("object", {}).get("metadata", {}).get("team_id") or event.get("team_id", "")
    subscriptions = STORE.list_subscriptions(team_id) if team_id else STORE.list_subscriptions()
    subscription = subscriptions[0] if subscriptions else None
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found for webhook")
    updated = apply_webhook(event, subscription)
    return {"subscription": updated.model_dump(mode="json")}


@app.post("/api/v1/jobs")
def enqueue_job(request: QueueJobRequest) -> dict:
    job = queue_job(request.kind, request.project_id, request.payload)
    STORE.save_job(job)
    return job.model_dump(mode="json")


@app.get("/api/v1/jobs/health")
def jobs_health() -> dict:
    return job_health()


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = STORE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump(mode="json")


@app.get("/api/v1/admin/live")
def admin_live() -> dict:
    return {"status": "live", "product": "AI Scientist Platform"}


@app.get("/api/v1/admin/ready")
def admin_ready() -> dict:
    health = admin_health()
    required = [health["database"], health["redis_workers"], health["storage"]]
    ready = all(item.get("status") in {"ready", "local-fallback", "fallback"} for item in required)
    if settings.production:
        ready = all(item.get("status") == "ready" for item in required)
    if not ready:
        raise HTTPException(status_code=503, detail=health)
    return {"status": "ready", "checks": health}


@app.get("/api/v1/admin/migrations/bootstrap.sql", response_class=PlainTextResponse)
def migration_bootstrap_sql() -> str:
    return ALEMBIC_BOOTSTRAP_SQL


@app.get("/api/projects", response_model=list[ResearchProject])
def list_projects() -> list[ResearchProject]:
    projects = STORE.list_projects()
    if not projects:
        return [create_default_project()]
    return projects


@app.post("/api/projects", response_model=ResearchProject)
def create_project(request: CreateProjectRequest) -> ResearchProject:
    project = ResearchProject(
        id=new_id("project"),
        name=request.name,
        description=request.description,
        created_at=utc_now(),
    )
    return STORE.save_project(project)


@app.get("/api/v1/projects", response_model=list[ResearchProject])
def list_projects_v1(request: Request) -> list[ResearchProject]:
    claims = current_claims(request)
    if claims:
        require_role(claims.role, "viewer")
        return [project for project in list_projects() if not project.team_id or project.team_id == claims.team_id]
    if settings.production:
        raise HTTPException(status_code=401, detail="Authentication required")
    return list_projects()


@app.post("/api/v1/projects", response_model=ResearchProject)
def create_project_v1(request: CreateProjectRequest, http_request: Request) -> ResearchProject:
    claims = current_claims(http_request)
    if claims:
        require_role(claims.role, "member")
    elif settings.production:
        raise HTTPException(status_code=401, detail="Authentication required")
    project = create_project(request)
    if claims:
        project.team_id = claims.team_id
        return STORE.save_project(project)
    return project


@app.get("/api/projects/{project_id}", response_model=ResearchProject)
def get_project(project_id: str) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/projects/{project_id}/questions/run", response_model=RunQuestionResponse)
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
    run, brief = ORCHESTRATOR.run(
        question,
        max_papers=request.max_papers,
        memory=project.memory if request.use_memory else [],
        extra_sources=extra_sources,
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


@app.post("/api/projects/{project_id}/papers/upload", response_model=UploadedPaper)
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


@app.get("/api/projects/{project_id}/papers", response_model=list[UploadedPaper])
def list_papers(project_id: str) -> list[UploadedPaper]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.uploaded_papers


@app.get("/api/projects/{project_id}/papers/{paper_id}", response_model=UploadedPaper)
def get_paper(project_id: str, paper_id: str) -> UploadedPaper:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@app.get("/api/projects/{project_id}/papers/{paper_id}/extractions", response_model=PaperExtractionSet)
def get_paper_extractions(project_id: str, paper_id: str) -> PaperExtractionSet:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper.extractions


<<<<<<< HEAD
@app.get("/api/connectors/status")
def connector_status() -> list:
    return ORCHESTRATOR.search_service.connector_status()


@app.get("/api/projects/{project_id}/embedding-status")
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


@app.get("/api/projects/{project_id}/papers/{paper_id}/chunks")
def ranked_paper_chunks(project_id: str, paper_id: str, ranked_by: str | None = None, query: str = "") -> dict:
    paper = STORE.get_uploaded_paper(project_id, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if ranked_by == "semantic" and query:
        ranking = rank_chunks(query, paper.chunks, limit=len(paper.chunks) or 8)
    else:
        ranking = []
    return {"paper_id": paper_id, "chunks": paper.chunks, "ranking": ranking}


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
@app.post("/api/projects/{project_id}/memory", response_model=ResearchProject)
def add_memory(project_id: str, request: AddMemoryRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.memory.insert(
        0,
        MemoryItem(
            id=new_id("mem"),
            kind=request.kind,
            content=request.content,
            source_ids=request.source_ids,
            tags=request.tags,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.post("/api/projects/{project_id}/memory/promote", response_model=ResearchProject)
def promote_memory(project_id: str, request: PromoteMemoryRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    normalized_content = request.content.strip().lower()
    existing = next(
        (
            item
            for item in project.memory
            if item.kind == request.kind and item.content.strip().lower() == normalized_content and item.status == "active"
        ),
        None,
    )
    if existing:
        existing.source_ids = sorted(set(existing.source_ids + request.source_ids))
        existing.tags = sorted(set(existing.tags + request.tags + ["promoted"]))
    else:
        project.memory.insert(
            0,
            MemoryItem(
                id=new_id("mem"),
                kind=request.kind,
                content=request.content.strip(),
                source_ids=request.source_ids,
                tags=sorted(set(request.tags + ["promoted"])),
                created_at=utc_now(),
            ),
        )
    return STORE.save_project(project)


@app.get("/api/projects/{project_id}/memory", response_model=list[MemoryItem])
def list_memory(project_id: str, kind: str | None = None, q: str | None = None) -> list[MemoryItem]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    items = project.memory
    if kind:
        items = [item for item in items if item.kind == kind]
    if q:
        query = q.lower()
        items = [
            item
            for item in items
            if query in item.content.lower() or any(query in tag.lower() for tag in item.tags)
        ]
    return items


@app.post("/api/projects/{project_id}/collections", response_model=ResearchProject)
def create_collection(project_id: str, request: CreateCollectionRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.source_collections.insert(
        0,
        SourceCollection(
            id=new_id("collection"),
            name=request.name,
            description=request.description,
            source_ids=request.source_ids,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.post("/api/projects/{project_id}/annotations", response_model=ResearchProject)
def add_annotation(project_id: str, request: AddAnnotationRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.annotations.insert(
        0,
        ResearchAnnotation(
            id=new_id("ann"),
            target_type=request.target_type,
            target_id=request.target_id,
            note=request.note,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.post("/api/projects/{project_id}/experiment-plans", response_model=ResearchProject)
def create_plan(project_id: str, request: CreateExperimentPlanRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    brief = resolve_brief(project, request.brief_id, request.question_id)
    plan = create_experiment_plan(
        brief,
        objective=request.objective,
        memory=project.memory,
        hypothesis_id=request.hypothesis_id,
        template_id=request.template_id,
        status=request.status,
    )
    project.experiment_plans.insert(0, plan)
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind="experiment_plan",
            status="completed",
            title=plan.title,
            summary="Generated datasets, baselines, metrics, ablations, validation protocol, and implementation scaffold.",
            target_id=plan.id,
            created_at=utc_now(),
            completed_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.get("/api/experiment-templates")
def experiment_templates() -> list[dict]:
    return list_templates()


@app.post("/api/projects/{project_id}/experiment-plans/recommend")
def recommend_plan(project_id: str, request: RecommendExperimentPlanRequest) -> dict:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = resolve_brief(project, request.brief_id, None) if request.brief_id or project.briefs else None
    question = request.question or (brief.title if brief else "")
    return recommend_experiment_plan(brief, question=question, domain=request.domain, task=request.task, top_k=request.top_k)


@app.patch("/api/projects/{project_id}/experiment-plans/{plan_id}", response_model=ExperimentPlan)
def update_plan(project_id: str, plan_id: str, request: UpdateExperimentPlanRequest) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(plan, field, value)
    STORE.save_project(project)
    return plan


@app.post("/api/projects/{project_id}/experiment-plans/{plan_id}/generate-script", response_model=ExperimentPlan)
def generate_plan_script(project_id: str, plan_id: str, request: GenerateScriptRequest | None = None) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    if request:
        if request.validation_tests:
            plan.validation_plan.statistical_tests = request.validation_tests
        if request.confidence_interval:
            plan.validation_plan.confidence_interval = request.confidence_interval
        if request.correction:
            plan.validation_plan.correction = request.correction
    plan.generated_script = generate_script(plan)
    plan.implementation_template = plan.generated_script
    object_record = OBJECT_STORE.put_bytes(project_id, "script", f"{plan.id}.py", plan.generated_script.encode("utf-8"), "text/x-python")
    STORE.save_object_record(object_record)
    job = queue_job("script_generation", project_id, {"plan_id": plan.id, "object_id": object_record.id})
    STORE.save_job(job)
    STORE.save_project(project)
    return plan


@app.get("/api/projects/{project_id}/experiment-plans/{plan_id}/script.py", response_class=PlainTextResponse)
def get_plan_script(project_id: str, plan_id: str) -> PlainTextResponse:
    plan = get_plan(project_id, plan_id)
    script = plan.generated_script or generate_script(plan)
    return PlainTextResponse(
        script,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{plan.id}.py"'},
    )


@app.get("/api/projects/{project_id}/experiment-plans/{plan_id}", response_model=ExperimentPlan)
def get_plan(project_id: str, plan_id: str) -> ExperimentPlan:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Experiment plan not found")
    return plan


@app.get("/api/projects/{project_id}/experiment-plans/{plan_id}/export.md", response_class=PlainTextResponse)
def export_plan(project_id: str, plan_id: str) -> PlainTextResponse:
    plan = get_plan(project_id, plan_id)
    return PlainTextResponse(
        experiment_plan_to_markdown(plan),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{plan.id}.md"'},
    )


@app.post("/api/projects/{project_id}/tasks", response_model=ResearchProject)
def create_task(project_id: str, request: CreateResearchTaskRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind=request.kind,
            status="queued",
            title=request.title,
            summary=request.summary,
            target_id=request.target_id,
            created_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.get("/api/projects/{project_id}/graph", response_model=ResearchGraph)
def get_graph(project_id: str) -> ResearchGraph:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return build_research_graph(project)


@app.get("/api/projects/{project_id}/graph/export.json")
def export_graph_json(project_id: str) -> dict:
    graph = get_graph(project_id)
    return graph.model_dump(mode="json")


@app.get("/api/projects/{project_id}/graph/export.svg", response_class=PlainTextResponse)
def export_graph_svg(project_id: str) -> PlainTextResponse:
    graph = get_graph(project_id)
    rows = []
    for index, node in enumerate(graph.nodes[:80]):
        y = 30 + index * 24
        rows.append(f'<text x="20" y="{y}" font-size="12">{escape_xml(node.kind)}: {escape_xml(node.label[:80])}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{max(120, 60 + len(rows) * 24)}">{"".join(rows)}</svg>'
    return PlainTextResponse(svg, media_type="image/svg+xml")


@app.get("/api/v1/projects/{project_id}/artifacts")
def list_project_artifacts(project_id: str, request: Request) -> list[dict]:
    require_project_access(request, project_id, "viewer")
    return [record.model_dump(mode="json") for record in STORE.list_object_records(project_id)]


@app.get("/api/v1/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, request: Request) -> Response:
    record = STORE.get_object_record(artifact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if record.project_id:
        require_project_access(request, record.project_id, "viewer")
    content = OBJECT_STORE.read_bytes(record)
    filename = record.name or artifact_id
    return Response(
        content=content,
        media_type=record.content_type,
        headers={"content-disposition": f'attachment; filename="{Path(filename).name}"'},
    )


@app.post("/api/projects/{project_id}/hypotheses", response_model=ResearchProject)
def create_hypotheses(project_id: str, request: GenerateHypothesesRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    brief = resolve_brief(project, request.brief_id, None)
    experiment_plan = resolve_experiment_plan(project, request.experiment_plan_id)
    hypotheses = generate_hypotheses(
        brief,
        memory=project.memory,
        experiment_plan=experiment_plan,
        max_hypotheses=request.max_hypotheses,
    )
    project.hypotheses = hypotheses + project.hypotheses
    project.tasks.insert(
        0,
        ResearchTask(
            id=new_id("task"),
            kind="hypothesis_generation",
            status="completed",
            title=f"Generated {len(hypotheses)} hypotheses",
            summary="Created grounded hypothesis candidates from evidence, methodology gaps, memory, and experiment plans.",
            target_id=hypotheses[0].id if hypotheses else None,
            created_at=utc_now(),
            completed_at=utc_now(),
        ),
    )
    return STORE.save_project(project)


@app.get("/api/projects/{project_id}/hypotheses", response_model=list[HypothesisCandidate])
def list_hypotheses(project_id: str) -> list[HypothesisCandidate]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.hypotheses


@app.get("/api/projects/{project_id}/briefs/{brief_id}")
def get_brief(project_id: str, brief_id: str):
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = next((item for item in project.briefs if item.id == brief_id), None)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@app.get("/api/projects/{project_id}/briefs/{brief_id}/quality", response_model=EvidenceQualityReport)
def get_brief_quality(project_id: str, brief_id: str) -> EvidenceQualityReport:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    brief = next((item for item in project.briefs if item.id == brief_id), None)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.quality_report:
        return brief.quality_report
    if brief.quality_report_id:
        report = STORE.get_quality_report(project_id, brief.quality_report_id)
        if report:
            return report
    report = next((item for item in project.quality_reports if item.brief_id == brief_id), None)
    if report:
        return report
    raise HTTPException(status_code=404, detail="Quality report not found")


<<<<<<< HEAD
@app.get("/api/projects/{project_id}/runs/{run_id}/events")
def run_events(project_id: str, run_id: str) -> StreamingResponse:
    project = STORE.get_project(project_id)
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


@app.patch("/api/projects/{project_id}/evidence/{evidence_id}/feedback", response_model=ResearchProject)
def evidence_feedback(project_id: str, evidence_id: str, request: EvidenceFeedbackRequest) -> ResearchProject:
    project = STORE.get_project(project_id)
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
    return STORE.save_project(project)


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
@app.get("/api/projects/{project_id}/briefs/{brief_id}/export.md", response_class=PlainTextResponse)
def export_brief(project_id: str, brief_id: str) -> PlainTextResponse:
    project = STORE.get_project(project_id)
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


@app.get("/api/projects/{project_id}/briefs/{brief_id}/export.pdf")
def export_brief_pdf(project_id: str, brief_id: str) -> Response:
    markdown = export_brief(project_id, brief_id).body.decode("utf-8")
    try:
        from weasyprint import HTML  # type: ignore

        pdf = HTML(string=f"<pre>{escape_xml(markdown)}</pre>").write_pdf()
        return Response(pdf, media_type="application/pdf")
    except Exception:
        return PlainTextResponse(
            "PDF export fallback: install WeasyPrint to render PDF.\n\n" + markdown,
            media_type="text/plain",
        )


@app.get("/api/projects/{project_id}/briefs/{brief_id}/export.tex", response_class=PlainTextResponse)
def export_brief_tex(project_id: str, brief_id: str) -> PlainTextResponse:
    markdown = export_brief(project_id, brief_id).body.decode("utf-8")
    tex = "\\section*{AI Scientist Brief}\n\\begin{verbatim}\n" + markdown + "\\end{verbatim}\n"
    return PlainTextResponse(tex, media_type="application/x-tex")


@app.post("/api/v1/agents", response_model=ResearchProject)
def create_agent(request: CreateAgentRequest, project_id: str = "project_demo") -> ResearchProject:
    project = STORE.get_project(project_id) or create_default_project()
    agent = AgentDefinition(
        id=new_id("agent"),
        project_id=project.id,
        type=request.type,
        name=request.name,
        goal=request.goal,
        schedule=request.schedule,
        created_at=utc_now(),
    )
    project.autonomous_agents.insert(0, agent)
    run = start_agent_run(project, agent)
    if request.type == "experiment_runner":
        request_experiment_approval(run, None)
    return STORE.save_project(project)


@app.post("/api/v1/projects/{project_id}/agents", response_model=ResearchProject)
def create_project_agent(project_id: str, request: CreateAgentRequest, http_request: Request) -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    return create_agent(request, project_id)


@app.post("/api/v1/saved-searches", response_model=ResearchProject)
def create_saved_search(request: CreateSavedSearchRequest, http_request: Request) -> ResearchProject:
    require_project_access(http_request, request.project_id, "member")
    project = STORE.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    create_saved_search_record(project, request.query, request.cadence)
    return STORE.save_project(project)


@app.post("/api/v1/agent-runs/{run_id}/step", response_model=ResearchProject)
def run_agent_step(run_id: str, request: RunAgentStepRequest, http_request: Request, project_id: str = "project_demo") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    agent = next((item for item in project.autonomous_agents if item.id == run.agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.type == "literature_monitor":
        search = create_saved_search_record(project, request.query or agent.goal, agent.schedule or "weekly")
        literature_monitor_step(project, run, search.query)
        complete_literature_monitor(project, run, search)
    elif agent.type == "experiment_runner":
        if not request.approve and not any(decision.approved for decision in run.decisions if decision.requires_approval):
            request_experiment_approval(run, request.experiment_plan_id)
        else:
            run.status = "running"
            run.current_step = "ready_for_sandbox"
            run.steps.append({"name": "approval_checked", "status": "completed", "created_at": utc_now()})
    else:
        run.status = "completed"
        run.current_step = "workflow_recorded"
        run.completed_at = utc_now()
        run.steps.append({"name": agent.type, "status": "completed", "created_at": utc_now()})
    return STORE.save_project(project)


@app.post("/api/v1/agent-runs/{run_id}/sandbox", response_model=ResearchProject)
def run_agent_sandbox(run_id: str, request: SandboxRunRequest, http_request: Request, project_id: str = "project_demo") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if not any(decision.approved for decision in run.decisions if decision.requires_approval):
        raise HTTPException(status_code=409, detail="Sandbox execution requires an approved agent decision")
    result = run_sandbox(request.script, timeout_seconds=request.timeout_seconds)
    record_execution_artifact(project, run, "stdout", result.get("stdout", ""))
    if result.get("stderr"):
        record_execution_artifact(project, run, "stderr", result["stderr"])
    run.status = "completed" if result["exit_code"] == 0 else "failed"
    run.current_step = "sandbox_completed"
    run.completed_at = utc_now()
    return STORE.save_project(project)


@app.post("/api/v1/agents/{agent_id}/pause", response_model=ResearchProject)
def pause_agent(agent_id: str, project_id: str = "project_demo") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "paused")


@app.post("/api/v1/agents/{agent_id}/resume", response_model=ResearchProject)
def resume_agent_status(agent_id: str, project_id: str = "project_demo") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "active")


@app.post("/api/v1/agents/{agent_id}/stop", response_model=ResearchProject)
def stop_agent(agent_id: str, project_id: str = "project_demo") -> ResearchProject:
    return set_agent_status(project_id, agent_id, "stopped")


@app.post("/api/v1/agent-runs/{run_id}/approve", response_model=ResearchProject)
def approve_agent_run(run_id: str, http_request: Request, project_id: str = "project_demo") -> ResearchProject:
    require_project_access(http_request, project_id, "member")
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    run.status = "running"
    run.current_step = "approved_for_next_action"
    run.decisions.append(
        AgentDecision(
            id=new_id("decision"),
            agent_id=run.agent_id,
            run_id=run.id,
            action="approve_next_action",
            reason="Human approval recorded for supervised autonomous workflow.",
            requires_approval=True,
            approved=True,
            created_at=utc_now(),
        )
    )
    return STORE.save_project(project)


@app.get("/api/v1/agent-runs/{run_id}/status")
def agent_run_status(run_id: str, request: Request, project_id: str = "project_demo") -> dict:
    require_project_access(request, project_id, "viewer")
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {"id": run.id, "status": run.status, "current_step": run.current_step, "steps": run.steps}


@app.get("/api/v1/agent-runs/{run_id}/audit")
def agent_run_audit(run_id: str, request: Request, project_id: str = "project_demo") -> dict:
    require_project_access(request, project_id, "viewer")
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = next((item for item in project.autonomous_agent_runs if item.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run.model_dump(mode="json")


@app.get("/api/v1/admin/health")
def admin_health() -> dict:
    return {
        "database": database_health(),
        "redis_workers": job_health(),
        "storage": storage_health(),
        "sandbox": {"backend": settings.sandbox_backend, "image": settings.sandbox_image},
        "connectors": [item.model_dump(mode="json") for item in ORCHESTRATOR.search_service.connector_status()],
        "billing": "stripe-test" if settings.stripe_secret_key else "stripe-test-stub",
    }


def resolve_brief(project: ResearchProject, brief_id: str | None, question_id: str | None):
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


def resolve_experiment_plan(project: ResearchProject, plan_id: str | None) -> ExperimentPlan | None:
    if plan_id:
        plan = next((item for item in project.experiment_plans if item.id == plan_id), None)
        if not plan:
            raise HTTPException(status_code=404, detail="Experiment plan not found")
        return plan
    return project.experiment_plans[0] if project.experiment_plans else None


def create_default_project() -> ResearchProject:
    project = ResearchProject(
        id="project_demo",
        name="AI Research OS Demo",
        description="A starter workspace for citation-grounded literature investigation.",
        created_at=utc_now(),
    )
    STORE.save_project(project)
    return project


def v2_v3_workspace_html() -> str:
    return """
<!doctype html>
<html>
<head>
  <title>AI Scientist V2/V3 Workspace</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body{margin:0;background:#f7f8f5;color:#17211f;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
    main{max-width:1180px;margin:auto;padding:28px;display:grid;gap:22px}
    header{display:flex;justify-content:space-between;align-items:end;gap:16px;border-bottom:1px solid #d9ded8;padding-bottom:18px}
    h1{font-size:34px;margin:0}.eyebrow{font-size:12px;text-transform:uppercase;color:#08735f;font-weight:800;margin:0 0 6px}
    .grid{display:grid;gap:16px}.stats{grid-template-columns:repeat(5,minmax(0,1fr))}.cols{grid-template-columns:1.25fr .75fr}
    .card{background:white;border:1px solid #d9ded8;border-radius:8px;padding:18px}.stat strong{font-size:26px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.stat small{color:#64736f}
    .stat span,.muted{color:#64736f}button,a.button{border:1px solid #16443c;background:white;color:#16443c;border-radius:6px;padding:10px 12px;font-weight:800;text-decoration:none;cursor:pointer}
    button.primary{background:#08735f;color:white;border-color:#08735f}input,select{border:1px solid #cdd5d1;border-radius:6px;padding:10px;font:inherit}
    form{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.list{display:grid;gap:10px}.item{border:1px solid #e1e6e2;border-radius:6px;padding:12px}
    .item p{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.badge{display:inline-block;border-radius:999px;background:#dff5eb;color:#075d4d;padding:4px 8px;font-size:11px;font-weight:800;text-transform:uppercase}.health-card{border:1px solid #e1e6e2;border-radius:6px;padding:12px;background:#f7f8f5}.actions{display:flex;gap:8px;flex-wrap:wrap}
    @media(max-width:820px){.stats,.cols,form{grid-template-columns:1fr}header{align-items:start;flex-direction:column}}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="eyebrow">V2/V3 Research OS</p>
      <h1>AI Scientist Workspace</h1>
      <p class="muted">Multi-user SaaS foundations, agents, approvals, billing, jobs, storage, and platform health.</p>
    </div>
    <div class="actions">
      <a class="button" href="/legacy">Legacy UI</a>
      <button class="primary" onclick="checkout()">Upgrade</button>
    </div>
  </header>
  <form onsubmit="signup(event)">
    <input id="email" value="owner@example.com" placeholder="email" />
    <input id="password" value="password123" placeholder="password" type="password" />
    <input id="team" value="Research Lab" placeholder="team" />
    <button class="primary">Sign up / refresh session</button>
  </form>
  <form onsubmit="createProject(event)">
    <select id="projectSelect" onchange="selectProject(event)"></select>
    <input id="newProjectName" placeholder="New project name" />
    <button>Create project</button>
  </form>
  <section class="grid stats">
    <div class="card stat"><span>Team</span><strong id="teamName">Local</strong><small>signed-in tenant</small></div>
    <div class="card stat"><span>Projects</span><strong id="projectCount">0</strong><small>available workspaces</small></div>
    <div class="card stat"><span>Briefs</span><strong id="briefCount">0</strong><small>generated syntheses</small></div>
    <div class="card stat"><span>Plans</span><strong id="planCount">0</strong><small>experiment packs</small></div>
    <div class="card stat"><span>Agents</span><strong id="agentCount">0</strong><small>supervised workflows</small></div>
  </section>
  <section class="grid cols">
    <div class="grid">
      <div class="card"><h2>Project Workspace</h2><p id="projectName" class="muted">Loading project...</p><div id="evidence" class="list"></div></div>
      <div class="card"><h2>Experiment Plans</h2><div id="plans" class="list"></div></div>
    </div>
    <aside class="grid">
      <div class="card">
        <h2>Agents</h2>
        <div class="actions">
          <button onclick="createAgent('literature_monitor')">Monitor</button>
          <button onclick="createAgent('experiment_runner')">Runner</button>
          <button class="primary" onclick="runAgent()">Run step</button>
        </div>
        <div id="agents" class="list" style="margin-top:12px"></div>
      </div>
      <div class="card"><h2>Notifications</h2><div id="notifications" class="list"></div></div>
      <div class="card"><h2>Platform Health</h2><div id="health" class="list">Loading...</div></div>
    </aside>
  </section>
</main>
<script>
  let state = {projects: [], session: {}, activeProjectId: ''};
  async function api(path, options) {
    const res = await fetch(path, options);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
  async function load() {
    state.session = await api('/api/v1/auth/session');
    state.projects = await api('/api/v1/projects');
    const health = await api('/api/v1/admin/health');
    if (!state.activeProjectId && state.projects.length) state.activeProjectId = state.projects[0].id;
    const p = state.projects.find(project => project.id === state.activeProjectId) || state.projects[0] || {};
    projectSelect.innerHTML = state.projects.map(project => `<option value="${project.id}" ${project.id === p.id ? 'selected' : ''}>${project.name}</option>`).join('');
    teamName.textContent = state.session.team?.name || 'Local';
    projectCount.textContent = state.projects.length || 0;
    briefCount.textContent = (p.briefs || []).length;
    planCount.textContent = (p.experiment_plans || []).length;
    agentCount.textContent = (p.autonomous_agents || []).length;
    projectName.textContent = p.name || 'No project yet';
    renderHealth(health);
    renderList('evidence', ((p.briefs || [])[0]?.evidence_items || []).slice(0, 6), x => `<span class="badge">${x.extraction_type}</span><p>${x.claim}</p><small>${x.source_id}</small>`, 'Run a question to populate evidence.');
    renderList('plans', (p.experiment_plans || []).slice(0, 4), x => `<b>${x.title}</b><p>${x.objective}</p><small>${x.status}</small>`, 'No experiment plans yet.');
    renderList('agents', (p.autonomous_agent_runs || []).slice(0, 5), x => `<span class="badge">${x.status}</span><p>${x.current_step}</p><small>${(x.decisions || []).length} decisions</small>${hasPendingApproval(x) ? `<div class="actions"><button onclick="approveRun('${x.id}')">Approve</button></div>` : ''}`, 'No agent runs yet.');
    renderList('notifications', (p.notifications || []).slice(0, 5), x => `<b>${x.title}</b><p>${x.body}</p>`, 'No notifications yet.');
  }
  function renderList(id, items, template, empty) {
    document.getElementById(id).innerHTML = items.length ? items.map(x => `<article class="item">${template(x)}</article>`).join('') : `<p class="muted">${empty}</p>`;
  }
  function renderHealth(health) {
    const keys = ['database', 'redis_workers', 'storage', 'sandbox'];
    document.getElementById('health').innerHTML = keys.map(key => {
      const value = health[key] || {};
      return `<article class="health-card"><b>${key.replace('_',' ')}</b><p class="muted">${value.status || value.backend || 'unknown'}</p></article>`;
    }).join('');
  }
  function activeProject() {
    return state.projects.find(project => project.id === state.activeProjectId) || state.projects[0];
  }
  function hasPendingApproval(run) {
    return (run.decisions || []).some(decision => decision.requires_approval && !decision.approved);
  }
  function selectProject(event) {
    state.activeProjectId = event.target.value;
    load();
  }
  async function createProject(event) {
    event.preventDefault();
    const name = newProjectName.value.trim(); if (!name) return;
    const project = await api('/api/v1/projects', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({name,description:'V2/V3 beta smoke workspace.'})});
    state.activeProjectId = project.id;
    newProjectName.value = '';
    await load();
  }
  async function signup(event) {
    event.preventDefault();
    try {
      await api('/api/v1/auth/signup', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({email:email.value,password:password.value,team_name:team.value})});
    } catch (e) {
      await api('/api/v1/auth/login', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({email:email.value,password:password.value})});
    }
    await load();
  }
  async function createAgent(type) {
    const p = activeProject(); if (!p) return;
    await api(`/api/v1/projects/${p.id}/agents`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({type,name:type.replace('_',' '),goal:'Prepare approved research workflow',schedule:'weekly'})});
    await load();
  }
  async function runAgent() {
    const p = activeProject(); const run = (p?.autonomous_agent_runs || []).find(hasPendingApproval) || p?.autonomous_agent_runs?.[0]; if (!run) return;
    await api(`/api/v1/agent-runs/${run.id}/step?project_id=${p.id}`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({query:'retrieval augmented research agents'})});
    await load();
  }
  async function approveRun(runId) {
    const p = activeProject(); if (!p) return;
    await api(`/api/v1/agent-runs/${runId}/approve?project_id=${p.id}`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({})});
    await load();
  }
  async function checkout() {
    const teamId = state.session.team?.id || 'local';
    const result = await api('/api/v1/billing/checkout', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({team_id:teamId,tier:'pro',success_url:location.href,cancel_url:location.href})});
    alert('Checkout ready: ' + result.url);
  }
  load();
</script>
</body>
</html>
"""


def build_memory_from_brief(brief) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    for content in brief.open_problems[:2]:
        items.append(MemoryItem(id=new_id("mem"), kind="gap", content=content, tags=["auto", "open-problem"], created_at=utc_now()))
    for content in brief.suggested_next_directions[:2]:
        items.append(MemoryItem(id=new_id("mem"), kind="idea", content=content, tags=["auto", "next-direction"], created_at=utc_now()))
    return items


<<<<<<< HEAD
def set_agent_status(project_id: str, agent_id: str, status: str) -> ResearchProject:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agent = next((item for item in project.autonomous_agents if item.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = status  # type: ignore[assignment]
    for run in project.autonomous_agent_runs:
        if run.agent_id == agent_id and run.status in {"queued", "running", "paused"}:
            run.status = "paused" if status == "paused" else "stopped" if status == "stopped" else "running"
            run.current_step = f"agent_{status}"
    return STORE.save_project(project)


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
async def read_upload(request: Request, fallback_filename: str) -> tuple[str, bytes, str]:
    content_type = request.headers.get("content-type", "application/pdf")
    body = await request.body()
    if not content_type.lower().startswith("multipart/form-data"):
        return fallback_filename, body, content_type

    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        payload = part.get_payload(decode=True) or b""
        part_filename = part.get_filename()
        if part_filename or part.get_param("name", header="content-disposition") in {"file", "paper", "upload"}:
            return part_filename or fallback_filename, payload, part.get_content_type() or "application/pdf"
    return fallback_filename, b"", content_type
