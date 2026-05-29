from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .agents import ResearchOrchestrator
from .ai_providers import build_provider
from .clerk import ClerkVerifier
from .config import settings
from .object_storage import ObjectStore
from .routes._auth import auth_middleware
from .routes._state import init_app
from .routes.admin import router as admin_router
from .routes.agents import router as agents_router
from .routes.artifacts import router as artifacts_router
from .routes.billing import router as billing_router
from .routes.briefs import router as briefs_router
from .routes.experiments import router as experiments_router
from .routes.frontend import router as frontend_router
from .routes.graph import router as graph_router
from .routes.hypotheses import router as hypotheses_router
from .routes.jobs import router as jobs_router
from .routes.memory import router as memory_router
from .routes.papers import router as papers_router
from .routes.projects import router as projects_router
from .routes.questions import router as questions_router
from .routes.settings import router as settings_router
from .store_factory import build_store

logger = logging.getLogger("ai_scientist")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

BASE_DIR = Path(__file__).resolve().parents[2]
STORE = build_store()
ORCHESTRATOR = ResearchOrchestrator(ai_provider=build_provider(settings.ai_provider, settings.model))
STATIC_DIR = Path(__file__).resolve().parent / "static"
OBJECT_STORE = ObjectStore()

CLERK_VERIFIER: ClerkVerifier | None = None
if settings.clerk_publishable_key:
    import base64
    try:
        encoded = settings.clerk_publishable_key.removeprefix("pk_test_").rstrip("$")
        domain = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        issuer = f"https://{domain}"
        CLERK_VERIFIER = ClerkVerifier(jwks_url=jwks_url, issuer=issuer)
    except Exception as exc:
        logger.warning("Failed to init Clerk verifier: %s", exc)

init_app(STORE, ORCHESTRATOR, OBJECT_STORE, CLERK_VERIFIER, BASE_DIR)

@asynccontextmanager
async def lifespan(application: FastAPI):
    validate_production_configuration()
    yield


app = FastAPI(
    title="Research Assistant",
    description="Citation-grounded research intelligence workspace.",
    version="0.1.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url] if settings.production else [settings.public_base_url, "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


app.middleware("http")(auth_middleware)


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


def validate_production_configuration() -> None:
    settings.validate()


@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("api_error path=%s method=%s error=%s", request.url.path, request.method, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "Research Assistant",
        "mode": "research-intelligence-beta",
        "storage": settings.store_backend or "sqlite",
        "ai_provider": settings.ai_provider,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "api_versions": ["legacy", "v1"],
    }


@app.get("/api/v1/health")
def versioned_health() -> dict:
    return health()


app.include_router(projects_router)
app.include_router(questions_router)
app.include_router(papers_router)
app.include_router(memory_router)
app.include_router(experiments_router)
app.include_router(agents_router)
app.include_router(graph_router)
app.include_router(hypotheses_router)
app.include_router(briefs_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(settings_router)
app.include_router(jobs_router)
app.include_router(artifacts_router)
app.include_router(frontend_router)

FRONTEND_DIR = BASE_DIR / "frontend" / "out"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
