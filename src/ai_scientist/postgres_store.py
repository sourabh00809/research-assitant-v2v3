from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from .config import settings
from .models import (
    DocumentChunk,
    EvidenceQualityReport,
    JobRecord,
    ObjectStorageRecord,
    ResearchProject,
    SubscriptionRecord,
    Team,
    TeamMembership,
    TenantUser,
    UploadedPaper,
    UsageEvent,
)


class PostgresStore:
    """Production JSONB persistence.

    The domain models remain Pydantic-first while Postgres becomes the durable
    source of truth. Narrow indexes live beside JSONB payloads for listing,
    health checks, and future relational queries.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or settings.database_url
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgresStore")
        self._bootstrap()

    def list_projects(self) -> list[ResearchProject]:
        rows = self._fetch_all("select payload from projects order by created_at desc")
        return [ResearchProject.model_validate(row["payload"]) for row in rows]

    def delete_project(self, project_id: str) -> None:
        self._execute("delete from projects where id = %s", (project_id,))

    def get_project(self, project_id: str) -> ResearchProject | None:
        row = self._fetch_one("select payload from projects where id = %s", (project_id,))
        return ResearchProject.model_validate(row["payload"]) if row else None

    def update_project(self, project_id: str, mutator) -> ResearchProject | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select payload from projects where id = %s for update", (project_id,))
                row = cur.fetchone()
                if not row:
                    return None
                project = ResearchProject.model_validate(row["payload"])
                mutator(project)
                cur.execute(
                    """
                    insert into projects (id, team_id, name, created_at, payload)
                    values (%s, %s, %s, %s, %s::jsonb)
                    on conflict(id) do update set
                        team_id = excluded.team_id,
                        name = excluded.name,
                        created_at = excluded.created_at,
                        payload = excluded.payload
                    """,
                    (project.id, project.team_id, project.name, project.created_at, _dump(project)),
                )
            conn.commit()
        return project

    def save_project(self, project: ResearchProject) -> ResearchProject:
        self._execute(
            """
            insert into projects (id, team_id, name, created_at, payload)
            values (%s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                team_id = excluded.team_id,
                name = excluded.name,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (project.id, project.team_id, project.name, project.created_at, _dump(project)),
        )
        return project

    def save_question(self, project_id: str, question) -> Any:
        self.update_project(project_id, lambda p: setattr(p, "questions",
            [question] + [item for item in p.questions if item.id != question.id]))
        return question

    def save_brief(self, project_id: str, brief) -> Any:
        self.update_project(project_id, lambda p: setattr(p, "briefs",
            [brief] + [item for item in p.briefs if item.id != brief.id]))
        return brief

    def save_memory_item(self, project_id: str, item) -> Any:
        self.update_project(project_id, lambda p: setattr(p, "memory",
            [item] + [existing for existing in p.memory if existing.id != item.id]))
        return item

    def list_document_chunks(self, project_id: str, limit: int = 8) -> list[DocumentChunk]:
        project = self.get_project(project_id)
        if not project:
            return []
        chunks: list[DocumentChunk] = []
        for paper in project.uploaded_papers:
            chunks.extend(paper.chunks)
        return sorted(chunks, key=lambda item: item.created_at, reverse=True)[:limit]

    def get_uploaded_paper(self, project_id: str, paper_id: str) -> UploadedPaper | None:
        project = self.get_project(project_id)
        if not project:
            return None
        return next((paper for paper in project.uploaded_papers if paper.id == paper_id), None)

    def list_uploaded_papers(self, project_id: str) -> list[UploadedPaper]:
        project = self.get_project(project_id)
        return project.uploaded_papers if project else []

    def save_uploaded_paper(self, project_id: str, paper: UploadedPaper) -> UploadedPaper:
        def _mutate(p):
            p.uploaded_papers = [item for item in p.uploaded_papers if item.id != paper.id]
            p.uploaded_papers.insert(0, paper)
        self.update_project(project_id, _mutate)
        return paper

    def save_agent_run(self, project_id: str, run) -> Any:
        self.update_project(project_id, lambda p: setattr(p, "agent_runs",
            [run] + [item for item in p.agent_runs if item.id != run.id]))
        return run

    def list_agent_runs(self, project_id: str) -> list:
        project = self.get_project(project_id)
        return project.agent_runs if project else []

    def save_quality_report(self, project_id: str, report: EvidenceQualityReport) -> EvidenceQualityReport:
        self.update_project(project_id, lambda p: setattr(p, "quality_reports",
            [report] + [item for item in p.quality_reports if item.id != report.id]))
        return report

    def get_quality_report(self, project_id: str, report_id: str) -> EvidenceQualityReport | None:
        project = self.get_project(project_id)
        if not project:
            return None
        return next((report for report in project.quality_reports if report.id == report_id), None)

    def save_tenant_bundle(
        self,
        user: TenantUser,
        team: Team,
        membership: TeamMembership,
        subscription: SubscriptionRecord,
    ) -> dict:
        self._upsert_global("tenant_users", user.id, user.created_at, user)
        self._upsert_global("teams", team.id, team.created_at, team)
        self._upsert_global("team_memberships", membership.id, membership.created_at, membership)
        self._execute(
            """
            insert into subscriptions (id, team_id, tier, status, created_at, payload)
            values (%s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                team_id = excluded.team_id,
                tier = excluded.tier,
                status = excluded.status,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (subscription.id, subscription.team_id, subscription.tier, subscription.status, subscription.created_at, _dump(subscription)),
        )
        return {"user": user, "team": team, "membership": membership, "subscription": subscription}

    def list_users(self) -> list[TenantUser]:
        return [TenantUser.model_validate(row["payload"]) for row in self._fetch_all("select payload from tenant_users order by created_at desc")]

    def get_user_by_email(self, email: str) -> TenantUser | None:
        normalized = email.strip().lower()
        return next((user for user in self.list_users() if user.email.lower() == normalized), None)

    def get_user(self, user_id: str) -> TenantUser | None:
        row = self._fetch_one("select payload from tenant_users where id = %s", (user_id,))
        return TenantUser.model_validate(row["payload"]) if row else None

    def save_team(self, team: Team) -> None:
        self._upsert_global("teams", team.id, team.created_at, team)

    def get_team(self, team_id: str) -> Team | None:
        row = self._fetch_one("select payload from teams where id = %s", (team_id,))
        return Team.model_validate(row["payload"]) if row else None

    def list_teams(self) -> list[Team]:
        return [Team.model_validate(row["payload"]) for row in self._fetch_all("select payload from teams order by created_at desc")]

    def list_team_memberships(self, user_id: str | None = None, team_id: str | None = None) -> list[TeamMembership]:
        rows = self._fetch_all("select payload from team_memberships order by created_at desc")
        memberships = [TeamMembership.model_validate(row["payload"]) for row in rows]
        if user_id:
            memberships = [item for item in memberships if item.user_id == user_id]
        if team_id:
            memberships = [item for item in memberships if item.team_id == team_id]
        return memberships

    def record_usage_event(self, event: UsageEvent) -> UsageEvent:
        self._execute(
            """
            insert into usage_events (id, subject_id, kind, quantity, created_at, payload)
            values (%s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                subject_id = excluded.subject_id,
                kind = excluded.kind,
                quantity = excluded.quantity,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (event.id, event.subject_id, event.kind, event.quantity, event.created_at, _dump(event)),
        )
        return event

    def list_usage_events(self, subject_id: str | None = None) -> list[UsageEvent]:
        if subject_id:
            rows = self._fetch_all("select payload from usage_events where subject_id = %s order by created_at desc", (subject_id,))
        else:
            rows = self._fetch_all("select payload from usage_events order by created_at desc")
        return [UsageEvent.model_validate(row["payload"]) for row in rows]

    def list_subscriptions(self, team_id: str | None = None) -> list[SubscriptionRecord]:
        if team_id:
            rows = self._fetch_all("select payload from subscriptions where team_id = %s order by created_at desc", (team_id,))
        else:
            rows = self._fetch_all("select payload from subscriptions order by created_at desc")
        return [SubscriptionRecord.model_validate(row["payload"]) for row in rows]

    def get_subscription(self, subscription_id: str) -> SubscriptionRecord | None:
        row = self._fetch_one("select payload from subscriptions where id = %s", (subscription_id,))
        return SubscriptionRecord.model_validate(row["payload"]) if row else None

    def save_subscription(self, subscription: SubscriptionRecord) -> None:
        self._execute(
            """
            insert into subscriptions (id, team_id, tier, status, created_at, payload)
            values (%s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                team_id = excluded.team_id,
                tier = excluded.tier,
                status = excluded.status,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (subscription.id, subscription.team_id, subscription.tier, subscription.status, subscription.created_at, _dump(subscription)),
        )

    def save_job(self, job: JobRecord) -> JobRecord:
        self._execute(
            """
            insert into jobs (id, project_id, kind, status, created_at, updated_at, payload)
            values (%s, %s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                project_id = excluded.project_id,
                kind = excluded.kind,
                status = excluded.status,
                updated_at = excluded.updated_at,
                payload = excluded.payload
            """,
            (job.id, job.project_id, job.kind, job.status, job.created_at, job.updated_at, _dump(job)),
        )
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        row = self._fetch_one("select payload from jobs where id = %s", (job_id,))
        return JobRecord.model_validate(row["payload"]) if row else None

    def list_jobs(self, project_id: str | None = None) -> list[JobRecord]:
        if project_id:
            rows = self._fetch_all("select payload from jobs where project_id = %s order by created_at desc", (project_id,))
        else:
            rows = self._fetch_all("select payload from jobs order by created_at desc")
        return [JobRecord.model_validate(row["payload"]) for row in rows]

    def save_object_record(self, record: ObjectStorageRecord) -> ObjectStorageRecord:
        self._execute(
            """
            insert into object_storage_records (id, project_id, kind, backend, uri, created_at, payload)
            values (%s, %s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set
                project_id = excluded.project_id,
                kind = excluded.kind,
                backend = excluded.backend,
                uri = excluded.uri,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (record.id, record.project_id, record.kind, record.backend, record.uri, record.created_at, _dump(record)),
        )
        return record

    def get_object_record(self, object_id: str) -> ObjectStorageRecord | None:
        row = self._fetch_one("select payload from object_storage_records where id = %s", (object_id,))
        return ObjectStorageRecord.model_validate(row["payload"]) if row else None

    def list_object_records(self, project_id: str | None = None) -> list[ObjectStorageRecord]:
        if project_id:
            rows = self._fetch_all("select payload from object_storage_records where project_id = %s order by created_at desc", (project_id,))
        else:
            rows = self._fetch_all("select payload from object_storage_records order by created_at desc")
        return [ObjectStorageRecord.model_validate(row["payload"]) for row in rows]

    def _bootstrap(self) -> None:
        from ._pgsql_schema import PGSQL_SCHEMA_SQL

        self._execute(PGSQL_SCHEMA_SQL)

    def _upsert_global(self, table: str, item_id: str, created_at: str, item: BaseModel) -> None:
        self._execute(
            f"""
            insert into {table} (id, created_at, payload)
            values (%s, %s, %s::jsonb)
            on conflict(id) do update set
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (item_id, created_at, _dump(item)),
        )

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _execute(self, sql: str, params: tuple | None = None) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()

    def _fetch_one(self, sql: str, params: tuple | None = None) -> dict | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    def _fetch_all(self, sql: str, params: tuple | None = None) -> list[dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())


def _dump(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"))
