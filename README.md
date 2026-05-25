# AI Scientist Platform MVP

A local, citation-grounded research workspace that turns a research question into an evidence-backed brief.

This implementation focuses on the first vertical slice from the product plan:

- project creation
- autonomous literature-style agent run
- paper relevance ranking
- structured evidence extraction
- methodology comparison matrix
- methodology quality scoring
- baseline and statistical validation critique
- critique and open-problem identification
- citation-grounded research brief
- Markdown export for generated briefs
- persistent project memory
- tagged manual memory capture
- memory-aware future research briefs
- source collections and annotations API foundations
- experiment design packs from generated briefs
- dataset, baseline, metric, ablation, and validation recommendations
- starter Python implementation scaffold for experiments
- research task records for generated planning work
- grounded hypothesis generation from evidence, memory, gaps, and experiment plans
- inspectable research graph connecting questions, briefs, evidence, memory, plans, and hypotheses
- SQLite production-beta persistence
- PDF upload with text and page-chunk ingestion
- optional OpenAI provider adapter with deterministic fallback
- single-user password gate
- Docker Compose deployment files
- V1.1 research intelligence: structured paper extractions, evidence quality reports, memory promotion, and richer research graph relationships
- V1.2 retrieval and RAG upgrade: deterministic local embeddings, hybrid semantic/keyword retrieval, connector status, PubMed metadata support, source deduplication, memory relevance scoring, chunk ranking, and retrieval transparency badges
- V1.3 Experiment Planning Pro: structured experiment plans, domain templates, dataset/baseline/metric recommendations, validation helpers, generated evaluation scripts, and planner API/UI surfaces
- V1.4 workspace scaffold: `/app` Next.js export placeholder, frontend source scaffold, SSE run events, evidence feedback, graph exports, and PDF/TeX export fallbacks
- V2/V3 foundations: migration command, normalized SaaS tenant/usage/subscription persistence, autonomous agent registry and workflow APIs, saved searches, notifications, audit trail records, execution artifacts, and a safe local sandbox fallback

The app uses FastAPI and a static browser UI. The backend API is intentionally clean enough for a future Next.js frontend to replace the static UI.

## Run

```powershell
python -m uvicorn ai_scientist.main:app --app-dir src --reload
```

## Production Beta Run

Copy `.env.example` to `.env`, set `AI_SCIENTIST_APP_PASSWORD`, then run:

```powershell
docker compose up --build
```

Persistent data lives in `./data` and uploaded PDFs live in `./storage`.

## Full V2/V3 Production Run

The production target is a single VM running Docker Compose with Caddy, FastAPI, Postgres + pgvector, Redis/Celery, MinIO, and a Docker-backed sandbox.

1. Copy and edit production secrets:

```powershell
Copy-Item .env.production.example .env.production
# Edit .env.production and replace every placeholder secret.
```

2. Point `AI_SCIENTIST_DOMAIN` at the VM, then deploy:

```powershell
.\scripts\deploy-prod.ps1
```

3. Run migrations and health checks:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend alembic upgrade head
curl https://YOUR_DOMAIN/api/v1/admin/live
curl https://YOUR_DOMAIN/api/v1/admin/ready
```

Production readiness expectations:

- `AI_SCIENTIST_ENV=production`
- `AI_SCIENTIST_STORE_BACKEND=postgres`
- strong `AI_SCIENTIST_APP_PASSWORD`, `AI_SCIENTIST_JWT_SECRET`, and `POSTGRES_PASSWORD`
- `AI_SCIENTIST_COOKIE_SECURE=true`
- `AI_SCIENTIST_STORAGE_BACKEND=minio`
- Docker socket access only on trusted single-tenant infrastructure for sandbox execution

Backups:

```powershell
.\scripts\backup-prod.ps1
```

Restore into a running clean stack:

```powershell
.\scripts\restore-prod.ps1 -BackupDir backups\YYYYMMDD-HHMMSS
```

For local Python runs, the same environment variables are supported:

```powershell
$env:AI_SCIENTIST_APP_PASSWORD="change-me"
$env:AI_SCIENTIST_DB_PATH="data/ai_scientist.db"
$env:AI_SCIENTIST_STORAGE_DIR="storage"
python -m uvicorn ai_scientist.main:app --app-dir src --reload
```

Then open:

```text
http://127.0.0.1:8000
```

If port 8000 is already occupied, use another port:

```powershell
python -m uvicorn ai_scientist.main:app --app-dir src --port 8001
```

## Optional External Search

By default, the MVP uses a built-in seed corpus so it works offline and is deterministic.

To try live arXiv and Semantic Scholar lookups:

```powershell
$env:AI_SCIENTIST_LIVE_SEARCH="1"
python -m uvicorn ai_scientist.main:app --app-dir src --reload
```

Live calls degrade gracefully to the local corpus if a network request fails.

## V1.2 Retrieval Settings

The default embedding path is local and deterministic, so it works offline without a model download:

```powershell
$env:AI_SCIENTIST_EMBEDDING_PROVIDER="local"
$env:AI_SCIENTIST_EMBEDDING_MODEL="deterministic-hash-v1"
```

PubMed is opt-in for live search:

```powershell
$env:AI_SCIENTIST_LIVE_SEARCH="1"
$env:AI_SCIENTIST_PUBMED_ENABLED="true"
# Optional, improves NCBI rate limits:
$env:NCBI_API_KEY="..."
```

## V1.3 Experiment Planner

Experiment templates live in `templates/experiment`. The planner works offline from local templates and extracted evidence, with optional external recommendation APIs:

```powershell
$env:AI_SCIENTIST_HF_ENABLED="true"
$env:HUGGINGFACE_API_TOKEN="..."
$env:AI_SCIENTIST_PWC_ENABLED="true"
$env:PAPERSWITHCODE_API_KEY="..."
```

Key endpoints:

```text
GET  /api/experiment-templates
POST /api/projects/{project_id}/experiment-plans/recommend
POST /api/projects/{project_id}/experiment-plans/{plan_id}/generate-script
GET  /api/projects/{project_id}/experiment-plans/{plan_id}/script.py
```

## V1.4+ Roadmap Foundations

The Next.js scaffold is in `frontend/`; the current beta serves a placeholder at `/app` until the static export exists. V2/V3 foundation modules include:

```powershell
python -m ai_scientist.migrate sqlite-to-postgres --sqlite data/ai_scientist.db --database-url postgresql://user:pass@localhost/db --dry-run
```

Autonomous-agent oversight APIs are exposed under `/api/v1/agents` and `/api/v1/agent-runs/{run_id}/audit`.

V2 platform endpoints now provide local beta contracts for the future Postgres/Redis/Celery stack:

```text
POST /api/v1/tenancy/bootstrap
POST /api/v1/usage
GET  /api/v1/usage/limits?subject_id=...&team_id=...
```

V3 autonomous workflow endpoints persist agent definitions, runs, decisions, saved searches, notifications, and execution artifacts in SQLite while keeping the production scheduler/worker boundary explicit:

```text
POST /api/v1/projects/{project_id}/agents
POST /api/v1/saved-searches
POST /api/v1/agent-runs/{run_id}/step?project_id=...
POST /api/v1/agent-runs/{run_id}/sandbox?project_id=...
GET  /api/v1/agent-runs/{run_id}/audit?project_id=...
```

## Test

```powershell
pytest
```
