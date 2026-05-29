"""
Canonical PostgreSQL DDL — single source of truth.

All PostgreSQL schema definitions should import from here
to avoid drift between postgres_store.py, platform_db.py,
and Alembic migrations.
"""

PGSQL_SCHEMA_SQL = """
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
create index if not exists idx_projects_team_id on projects(team_id);
create index if not exists idx_jobs_project_id on jobs(project_id);
create index if not exists idx_objects_project_id on object_storage_records(project_id);
"""
