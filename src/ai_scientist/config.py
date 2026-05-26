from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("AI_SCIENTIST_ENV", "development").lower()
        self.store_backend = os.getenv("AI_SCIENTIST_STORE_BACKEND", "").lower()
        self.db_path = Path(os.getenv("AI_SCIENTIST_DB_PATH", BASE_DIR / "data" / "ai_scientist.db"))
        self.database_url = os.getenv("DATABASE_URL", "")
        self.storage_backend = os.getenv("AI_SCIENTIST_STORAGE_BACKEND", "local").lower()
        self.storage_dir = Path(os.getenv("AI_SCIENTIST_STORAGE_DIR", BASE_DIR / "storage"))
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.jwt_secret = os.getenv("AI_SCIENTIST_JWT_SECRET", "dev-change-me")
        self.jwt_ttl_seconds = int(os.getenv("AI_SCIENTIST_JWT_TTL_SECONDS", "604800"))
        self.cookie_secure = os.getenv("AI_SCIENTIST_COOKIE_SECURE", "false").lower() == "true"
        self.cookie_samesite = os.getenv("AI_SCIENTIST_COOKIE_SAMESITE", "lax")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "research-assets")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
        self.openalex_enabled = os.getenv("AI_SCIENTIST_OPENALEX_ENABLED", "true").lower() == "true"
        self.core_enabled = os.getenv("AI_SCIENTIST_CORE_ENABLED", "true").lower() == "true"
        self.crossref_enabled = os.getenv("AI_SCIENTIST_CROSSREF_ENABLED", "true").lower() == "true"
        self.groq_enabled = os.getenv("AI_SCIENTIST_GROQ_ENABLED", "true").lower() == "true"
        self.sandbox_backend = os.getenv("AI_SCIENTIST_SANDBOX_BACKEND", "local").lower()
        self.sandbox_image = os.getenv("AI_SCIENTIST_SANDBOX_IMAGE", "python:3.11-slim")
        self.sandbox_cpu_quota = int(os.getenv("AI_SCIENTIST_SANDBOX_CPU_QUOTA", "50000"))
        self.sandbox_memory_mb = int(os.getenv("AI_SCIENTIST_SANDBOX_MEMORY_MB", "512"))
        self.worker_concurrency = int(os.getenv("AI_SCIENTIST_WORKER_CONCURRENCY", "2"))
        self.ai_provider = os.getenv("AI_SCIENTIST_AI_PROVIDER", "auto").lower()
        self.model = os.getenv("AI_SCIENTIST_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.app_password = os.getenv("AI_SCIENTIST_APP_PASSWORD", "")
        self.disable_auth = os.getenv("AI_SCIENTIST_DISABLE_AUTH", "").lower() in {"1", "true", "yes"}
        self.live_search = os.getenv("AI_SCIENTIST_LIVE_SEARCH", "1") == "1"
        self.embedding_provider = os.getenv("AI_SCIENTIST_EMBEDDING_PROVIDER", "local").lower()
        self.embedding_model = os.getenv("AI_SCIENTIST_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.pubmed_enabled = os.getenv("AI_SCIENTIST_PUBMED_ENABLED", "false").lower() == "true"
        self.ncbi_api_key = os.getenv("NCBI_API_KEY", "")
        self.hf_enabled = os.getenv("AI_SCIENTIST_HF_ENABLED", "false").lower() == "true"
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.pwc_enabled = os.getenv("AI_SCIENTIST_PWC_ENABLED", "false").lower() == "true"
        self.paperswithcode_api_key = os.getenv("PAPERSWITHCODE_API_KEY", "")
        self.max_papers = int(os.getenv("AI_SCIENTIST_MAX_PAPERS", "6"))
        self.max_chunks = int(os.getenv("AI_SCIENTIST_MAX_CHUNKS", "8"))
        self.public_base_url = os.getenv("AI_SCIENTIST_PUBLIC_BASE_URL", "http://127.0.0.1:8000")
        self.limit_free_agent_runs = int(os.getenv("AI_SCIENTIST_LIMIT_FREE_AGENT_RUNS", "50"))
        self.limit_free_projects = int(os.getenv("AI_SCIENTIST_LIMIT_FREE_PROJECTS", "3"))
        self.limit_free_storage_mb = int(os.getenv("AI_SCIENTIST_LIMIT_FREE_STORAGE_MB", "250"))
        self.limit_pro_agent_runs = int(os.getenv("AI_SCIENTIST_LIMIT_PRO_AGENT_RUNS", "1000"))
        self.limit_pro_projects = int(os.getenv("AI_SCIENTIST_LIMIT_PRO_PROJECTS", "100"))
        self.limit_pro_storage_mb = int(os.getenv("AI_SCIENTIST_LIMIT_PRO_STORAGE_MB", "10000"))
        self.limit_team_agent_runs = int(os.getenv("AI_SCIENTIST_LIMIT_TEAM_AGENT_RUNS", "5000"))
        self.limit_team_projects = int(os.getenv("AI_SCIENTIST_LIMIT_TEAM_PROJECTS", "1000"))
        self.limit_team_storage_mb = int(os.getenv("AI_SCIENTIST_LIMIT_TEAM_STORAGE_MB", "100000"))

    @property
    def production(self) -> bool:
        return self.environment in {"production", "prod"}

    @property
    def resolved_store_backend(self) -> str:
        if self.store_backend:
            return self.store_backend
        return "postgres" if self.production and self.database_url else "sqlite"

    def validate(self) -> None:
        warnings = []
        if self.production and self.jwt_secret == "dev-change-me":
            warnings.append("JWT_SECRET is still set to the default dev value")
        if self.production and self.app_password == "change-me":
            warnings.append("APP_PASSWORD is still set to the default dev value")
        if self.production and not self.cookie_secure:
            warnings.append("COOKIE_SECURE should be True in production")
        if warnings:
            raise RuntimeError("Production configuration warnings:\n" + "\n".join(warnings))


settings = Settings()
