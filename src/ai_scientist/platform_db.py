from __future__ import annotations

from .config import settings


def database_health() -> dict:
    if not settings.database_url:
        return {"backend": "sqlite", "status": "local-fallback", "url": str(settings.db_path)}
    try:
        import sqlalchemy as sa  # type: ignore

        engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sa.text("select 1"))
        return {"backend": "postgres", "status": "ready"}
    except Exception as exc:
        return {"backend": "postgres", "status": "degraded", "error": str(exc)}


ALEMBIC_BOOTSTRAP_SQL = """
create extension if not exists vector;
create table if not exists projects (
  id text primary key,
  team_id text,
  name text not null,
  created_at timestamptz not null,
  payload jsonb not null
);
create table if not exists tenant_users (id text primary key, created_at timestamptz not null, payload jsonb not null);
create table if not exists teams (id text primary key, created_at timestamptz not null, payload jsonb not null);
create table if not exists team_memberships (id text primary key, created_at timestamptz not null, payload jsonb not null);
create table if not exists subscriptions (
  id text primary key,
  team_id text not null,
  tier text not null,
  status text not null,
  created_at timestamptz not null,
  payload jsonb not null
);
create table if not exists usage_events (
  id text primary key,
  subject_id text not null,
  kind text not null,
  quantity integer not null,
  created_at timestamptz not null,
  payload jsonb not null
);
create table if not exists jobs (
  id text primary key,
  project_id text,
  kind text not null,
  status text not null,
  created_at timestamptz not null,
  updated_at timestamptz,
  payload jsonb not null
);
create table if not exists object_storage_records (
  id text primary key,
  project_id text,
  kind text not null,
  backend text not null,
  uri text not null,
  created_at timestamptz not null,
  payload jsonb not null
);
create table if not exists embeddings (
  id text primary key,
  artifact_type text not null,
  artifact_id text not null,
  model text not null,
  vector vector(384),
  created_at timestamptz not null
);
"""
