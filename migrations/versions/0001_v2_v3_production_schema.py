from __future__ import annotations

from alembic import op


revision = "0001_v2_v3_production_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
    )


def downgrade() -> None:
    op.execute(
        """
        drop table if exists embeddings;
        drop table if exists object_storage_records;
        drop table if exists jobs;
        drop table if exists usage_events;
        drop table if exists subscriptions;
        drop table if exists team_memberships;
        drop table if exists teams;
        drop table if exists tenant_users;
        drop table if exists projects;
        """
    )
