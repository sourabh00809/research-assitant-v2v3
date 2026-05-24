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
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.stripe_price_free = os.getenv("STRIPE_PRICE_FREE", "")
        self.stripe_price_pro = os.getenv("STRIPE_PRICE_PRO", "")
        self.stripe_price_team = os.getenv("STRIPE_PRICE_TEAM", "")
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_bucket = os.getenv("MINIO_BUCKET", "ai-scientist")
        self.sandbox_backend = os.getenv("AI_SCIENTIST_SANDBOX_BACKEND", "local").lower()
        self.sandbox_image = os.getenv("AI_SCIENTIST_SANDBOX_IMAGE", "python:3.11-slim")
        self.sandbox_cpu_quota = int(os.getenv("AI_SCIENTIST_SANDBOX_CPU_QUOTA", "50000"))
        self.sandbox_memory_mb = int(os.getenv("AI_SCIENTIST_SANDBOX_MEMORY_MB", "512"))
        self.worker_concurrency = int(os.getenv("AI_SCIENTIST_WORKER_CONCURRENCY", "2"))
        self.ai_provider = os.getenv("AI_SCIENTIST_AI_PROVIDER", "deterministic").lower()
        self.model = os.getenv("AI_SCIENTIST_MODEL", "gpt-4.1-mini")
        self.app_password = os.getenv("AI_SCIENTIST_APP_PASSWORD", "")
        self.live_search = os.getenv("AI_SCIENTIST_LIVE_SEARCH") == "1"
        self.embedding_provider = os.getenv("AI_SCIENTIST_EMBEDDING_PROVIDER", "local").lower()
        self.embedding_model = os.getenv("AI_SCIENTIST_EMBEDDING_MODEL", "deterministic-hash-v1")
        self.pubmed_enabled = os.getenv("AI_SCIENTIST_PUBMED_ENABLED", "false").lower() == "true"
        self.ncbi_api_key = os.getenv("NCBI_API_KEY", "")
        self.hf_enabled = os.getenv("AI_SCIENTIST_HF_ENABLED", "false").lower() == "true"
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.pwc_enabled = os.getenv("AI_SCIENTIST_PWC_ENABLED", "false").lower() == "true"
        self.paperswithcode_api_key = os.getenv("PAPERSWITHCODE_API_KEY", "")
        self.max_papers = int(os.getenv("AI_SCIENTIST_MAX_PAPERS", "6"))
        self.max_chunks = int(os.getenv("AI_SCIENTIST_MAX_CHUNKS", "8"))
        self.public_base_url = os.getenv("AI_SCIENTIST_PUBLIC_BASE_URL", "http://127.0.0.1:8000")

    @property
    def production(self) -> bool:
        return self.environment in {"production", "prod"}

    @property
    def resolved_store_backend(self) -> str:
        if self.store_backend:
            return self.store_backend
        return "postgres" if self.production and self.database_url else "sqlite"


settings = Settings()
