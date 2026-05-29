from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from threading import Lock
from typing import TypeVar

from pydantic import BaseModel

from .models import (
    AgentDecision,
    AgentDefinition,
    AgentRun,
    AgentRunRecord,
    AssumptionItem,
    BaselineMention,
    DatasetMention,
    DocumentChunk,
    EvidenceQualityReport,
    ExecutionArtifact,
    ExperimentPlan,
    ExtractedClaim,
    ExtractionArtifact,
    FutureWorkItem,
    HypothesisCandidate,
    IngestionRun,
    JobRecord,
    LimitationItem,
    MemoryItem,
    MethodologyItem,
    MetricMention,
    NotificationRecord,
    ObjectStorageRecord,
    PaperExtractionSet,
    ResearchAnnotation,
    ResearchBrief,
    ResearchProject,
    ResearchQuestion,
    ResearchTask,
    SavedSearch,
    SourceCollection,
    SubscriptionRecord,
    Team,
    TeamMembership,
    TenantUser,
    UploadedPaper,
    UsageEvent,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap()

    def list_projects(self) -> list[ResearchProject]:
        with self._connect() as conn:
            rows = conn.execute("select id from projects order by created_at desc").fetchall()
            return [self._assemble_project(conn, row["id"]) for row in rows]

    def get_project(self, project_id: str) -> ResearchProject | None:
        with self._connect() as conn:
            if not conn.execute("select 1 from projects where id = ?", (project_id,)).fetchone():
                return None
            return self._assemble_project(conn, project_id)

    def save_project(self, project: ResearchProject) -> ResearchProject:
        with self._lock, self._connect() as conn:
            self._save_project(conn, project)
        return project

    def delete_project(self, project_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("delete from projects where id = ?", (project_id,))

    def save_question(self, project_id: str, question: ResearchQuestion) -> ResearchQuestion:
        with self._lock, self._connect() as conn:
            self._insert_payload(conn, "questions", question.id, project_id, question.created_at, question)
        return question

    def save_brief(self, project_id: str, brief: ResearchBrief) -> ResearchBrief:
        with self._lock, self._connect() as conn:
            self._insert_payload(conn, "briefs", brief.id, project_id, brief.created_at, brief)
        return brief

    def save_memory_item(self, project_id: str, item: MemoryItem) -> MemoryItem:
        with self._lock, self._connect() as conn:
            self._insert_payload(conn, "memory", item.id, project_id, item.created_at, item)
        return item

    def save_uploaded_paper(self, project_id: str, paper: UploadedPaper) -> UploadedPaper:
        with self._lock, self._connect() as conn:
            self._save_uploaded_paper(conn, project_id, paper)
        return paper

    def list_uploaded_papers(self, project_id: str) -> list[UploadedPaper]:
        with self._connect() as conn:
            return self._list_uploaded_papers(conn, project_id)

    def get_uploaded_paper(self, project_id: str, paper_id: str) -> UploadedPaper | None:
        with self._connect() as conn:
            row = conn.execute(
                "select payload from uploaded_papers where project_id = ? and id = ?",
                (project_id, paper_id),
            ).fetchone()
            if not row:
                return None
            paper = UploadedPaper.model_validate(json.loads(row["payload"]))
            paper.chunks = self._list_chunks(conn, project_id, paper.id)
            paper.ingestion_runs = self._list_ingestion_runs(conn, project_id, paper.id)
            return paper

    def list_document_chunks(self, project_id: str, limit: int = 8) -> list[DocumentChunk]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select payload from document_chunks
                where project_id = ?
                order by created_at desc
                limit ?
                """,
                (project_id, limit),
            ).fetchall()
        return [DocumentChunk.model_validate(json.loads(row["payload"])) for row in rows]

    def save_agent_run(self, project_id: str, run: AgentRun) -> AgentRun:
        with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    insert into agent_runs (id, project_id, question_id, status, started_at, completed_at, provider, payload)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(id) do update set
                        question_id = excluded.question_id,
                        status = excluded.status,
                        completed_at = excluded.completed_at,
                        provider = excluded.provider,
                        payload = excluded.payload
                    """,
                    (
                        run.id,
                        project_id,
                        run.question_id,
                        run.status,
                        run.started_at,
                        run.completed_at,
                        run.provider,
                        _dump(run),
                    ),
                )
        return run

    def save_quality_report(self, project_id: str, report: EvidenceQualityReport) -> EvidenceQualityReport:
        with self._lock, self._connect() as conn:
            self._insert_payload(conn, "quality_reports", report.id, project_id, report.created_at, report)
        return report

    def get_quality_report(self, project_id: str, report_id: str) -> EvidenceQualityReport | None:
        with self._connect() as conn:
            row = conn.execute(
                "select payload from quality_reports where project_id = ? and id = ?",
                (project_id, report_id),
            ).fetchone()
        return EvidenceQualityReport.model_validate(json.loads(row["payload"])) if row else None

    def list_agent_runs(self, project_id: str) -> list[AgentRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "select payload from agent_runs where project_id = ? order by started_at desc",
                (project_id,),
            ).fetchall()
        return [AgentRun.model_validate(json.loads(row["payload"])) for row in rows]

    def save_tenant_bundle(
        self,
        user: TenantUser,
        team: Team,
        membership: TeamMembership,
        subscription: SubscriptionRecord,
    ) -> dict:
        with self._lock, self._connect() as conn:
                self._insert_global_payload(conn, "tenant_users", user.id, user.created_at, user)
                self._insert_global_payload(conn, "teams", team.id, team.created_at, team)
                self._insert_global_payload(conn, "team_memberships", membership.id, membership.created_at, membership)
                conn.execute(
                    """
                    insert into subscriptions (id, team_id, tier, status, created_at, payload)
                    values (?, ?, ?, ?, ?, ?)
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

    def record_usage_event(self, event: UsageEvent) -> UsageEvent:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                    insert into usage_events (id, subject_id, kind, quantity, created_at, payload)
                    values (?, ?, ?, ?, ?, ?)
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
        with self._connect() as conn:
            if subject_id:
                rows = conn.execute(
                    "select payload from usage_events where subject_id = ? order by created_at desc",
                    (subject_id,),
                ).fetchall()
            else:
                rows = conn.execute("select payload from usage_events order by created_at desc").fetchall()
        return [UsageEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def list_subscriptions(self, team_id: str | None = None) -> list[SubscriptionRecord]:
        with self._connect() as conn:
            rows = conn.execute("select payload from subscriptions order by created_at desc").fetchall()
        subscriptions = [SubscriptionRecord.model_validate(json.loads(row["payload"])) for row in rows]
        return [item for item in subscriptions if item.team_id == team_id] if team_id else subscriptions

    def get_subscription(self, subscription_id: str) -> SubscriptionRecord | None:
        with self._connect() as conn:
            row = conn.execute("select payload from subscriptions where id = ?", (subscription_id,)).fetchone()
        return SubscriptionRecord.model_validate(json.loads(row["payload"])) if row else None

    def save_subscription(self, subscription: SubscriptionRecord) -> None:
        with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    insert into subscriptions (id, team_id, tier, status, created_at, payload)
                    values (?, ?, ?, ?, ?, ?)
                    on conflict(id) do update set
                        team_id = excluded.team_id,
                        tier = excluded.tier,
                        status = excluded.status,
                        created_at = excluded.created_at,
                        payload = excluded.payload
                    """,
                    (subscription.id, subscription.team_id, subscription.tier, subscription.status, subscription.created_at, _dump(subscription)),
                )

    def list_users(self) -> list[TenantUser]:
        with self._connect() as conn:
            rows = conn.execute("select payload from tenant_users order by created_at desc").fetchall()
        return [TenantUser.model_validate(json.loads(row["payload"])) for row in rows]

    def get_user_by_email(self, email: str) -> TenantUser | None:
        normalized = email.strip().lower()
        return next((user for user in self.list_users() if user.email.lower() == normalized), None)

    def get_user(self, user_id: str) -> TenantUser | None:
        with self._connect() as conn:
            row = conn.execute("select payload from tenant_users where id = ?", (user_id,)).fetchone()
        return TenantUser.model_validate(json.loads(row["payload"])) if row else None

    def list_teams(self) -> list[Team]:
        with self._connect() as conn:
            rows = conn.execute("select payload from teams order by created_at desc").fetchall()
        return [Team.model_validate(json.loads(row["payload"])) for row in rows]

    def save_team(self, team: Team) -> None:
        with self._lock, self._connect() as conn:
            self._insert_global_payload(conn, "teams", team.id, team.created_at, team)

    def get_team(self, team_id: str) -> Team | None:
        with self._connect() as conn:
            row = conn.execute("select payload from teams where id = ?", (team_id,)).fetchone()
        return Team.model_validate(json.loads(row["payload"])) if row else None

    def list_team_memberships(self, user_id: str | None = None, team_id: str | None = None) -> list[TeamMembership]:
        with self._connect() as conn:
            rows = conn.execute("select payload from team_memberships order by created_at desc").fetchall()
        memberships = [TeamMembership.model_validate(json.loads(row["payload"])) for row in rows]
        if user_id:
            memberships = [item for item in memberships if item.user_id == user_id]
        if team_id:
            memberships = [item for item in memberships if item.team_id == team_id]
        return memberships

    def save_job(self, job: JobRecord) -> JobRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                    insert into jobs (id, project_id, kind, status, created_at, updated_at, payload)
                    values (?, ?, ?, ?, ?, ?, ?)
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
        with self._connect() as conn:
            row = conn.execute("select payload from jobs where id = ?", (job_id,)).fetchone()
        return JobRecord.model_validate(json.loads(row["payload"])) if row else None

    def list_jobs(self, project_id: str | None = None) -> list[JobRecord]:
        with self._connect() as conn:
            if project_id:
                rows = conn.execute(
                    "select payload from jobs where project_id = ? order by created_at desc",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute("select payload from jobs order by created_at desc").fetchall()
        return [JobRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def save_object_record(self, record: ObjectStorageRecord) -> ObjectStorageRecord:
        with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    insert into object_storage_records (id, project_id, kind, backend, uri, created_at, payload)
                    values (?, ?, ?, ?, ?, ?, ?)
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
        with self._connect() as conn:
            row = conn.execute("select payload from object_storage_records where id = ?", (object_id,)).fetchone()
        return ObjectStorageRecord.model_validate(json.loads(row["payload"])) if row else None

    def list_object_records(self, project_id: str | None = None) -> list[ObjectStorageRecord]:
        with self._connect() as conn:
            if project_id:
                rows = conn.execute(
                    "select payload from object_storage_records where project_id = ? order by created_at desc",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute("select payload from object_storage_records order by created_at desc").fetchall()
        return [ObjectStorageRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("pragma journal_mode = wal")
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("pragma synchronous = normal")
            conn.execute("pragma foreign_keys = on")
        return conn

    def _bootstrap(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists projects (
                    id text primary key,
                    name text not null,
                    description text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists questions (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists briefs (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists memory (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists experiment_plans (
                    id text primary key,
                    project_id text not null,
                    hypothesis_id text,
                    status text,
                    title text,
                    datasets text,
                    baselines text,
                    metrics text,
                    ablation_config text,
                    validation_plan text,
                    generated_script text,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists hypotheses (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists tasks (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists source_collections (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists annotations (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists uploaded_papers (
                    id text primary key,
                    project_id text not null,
                    title text not null,
                    filename text not null,
                    source_type text not null,
                    status text not null,
                    page_count integer not null,
                    chunk_count integer not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists document_chunks (
                    id text primary key,
                    paper_id text not null,
                    project_id text not null,
                    page_number integer not null,
                    created_at text not null,
                    text text not null,
                    payload text not null
                );
                create table if not exists ingestion_runs (
                    id text primary key,
                    paper_id text not null,
                    project_id text not null,
                    status text not null,
                    message text not null,
                    pages_extracted integer not null,
                    chunks_created integer not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists agent_runs (
                    id text primary key,
                    project_id text not null,
                    question_id text not null,
                    status text not null,
                    started_at text not null,
                    completed_at text,
                    provider text not null,
                    payload text not null
                );
                create table if not exists quality_reports (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists extracted_artifacts (
                    id text primary key,
                    project_id text not null,
                    paper_id text not null,
                    source_id text not null,
                    kind text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists tenant_users (
                    id text primary key,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists teams (
                    id text primary key,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists team_memberships (
                    id text primary key,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists project_memberships (
                    id text primary key,
                    project_id text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists usage_events (
                    id text primary key,
                    subject_id text not null,
                    kind text not null,
                    quantity integer not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists subscriptions (
                    id text primary key,
                    team_id text not null,
                    tier text not null,
                    status text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists autonomous_agents (
                    id text primary key,
                    project_id text not null,
                    type text not null,
                    status text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists autonomous_agent_runs (
                    id text primary key,
                    project_id text not null,
                    agent_id text not null,
                    status text not null,
                    current_step text not null,
                    created_at text not null,
                    completed_at text,
                    payload text not null
                );
                create table if not exists agent_decisions (
                    id text primary key,
                    project_id text not null,
                    agent_id text not null,
                    run_id text not null,
                    action text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists saved_searches (
                    id text primary key,
                    project_id text not null,
                    query text not null,
                    cadence text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists notifications (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists execution_artifacts (
                    id text primary key,
                    project_id text not null,
                    run_id text not null,
                    kind text not null,
                    created_at text not null,
                    payload text not null
                );
                create table if not exists jobs (
                    id text primary key,
                    project_id text,
                    kind text not null,
                    status text not null,
                    created_at text not null,
                    updated_at text,
                    payload text not null
                );
                create table if not exists object_storage_records (
                    id text primary key,
                    project_id text,
                    kind text not null,
                    backend text not null,
                    uri text not null,
                    created_at text not null,
                    payload text not null
                );
                """
            )
            self._ensure_column(conn, "uploaded_papers", "created_at text")
            self._ensure_column(conn, "experiment_plans", "hypothesis_id text")
            self._ensure_column(conn, "experiment_plans", "status text")
            self._ensure_column(conn, "experiment_plans", "title text")
            self._ensure_column(conn, "experiment_plans", "datasets text")
            self._ensure_column(conn, "experiment_plans", "baselines text")
            self._ensure_column(conn, "experiment_plans", "metrics text")
            self._ensure_column(conn, "experiment_plans", "ablation_config text")
            self._ensure_column(conn, "experiment_plans", "validation_plan text")
            self._ensure_column(conn, "experiment_plans", "generated_script text")
            self._ensure_column(conn, "document_chunks", "created_at text")
            self._ensure_column(conn, "document_chunks", "payload text")
            self._ensure_column(conn, "ingestion_runs", "payload text")
            self._ensure_column(conn, "agent_runs", "started_at text")
            self._ensure_column(conn, "agent_runs", "completed_at text")
            self._ensure_column(conn, "agent_runs", "provider text")

    def _save_project(self, conn: sqlite3.Connection, project: ResearchProject) -> None:
        conn.execute(
            """
            insert into projects (id, name, description, created_at, payload)
            values (?, ?, ?, ?, ?)
            on conflict(id) do update set
                name = excluded.name,
                description = excluded.description,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (project.id, project.name, project.description, project.created_at, _dump(project)),
        )
        self._replace_payloads(conn, "questions", project.id, project.questions)
        self._replace_payloads(conn, "briefs", project.id, project.briefs)
        self._replace_payloads(conn, "memory", project.id, project.memory)
        self._replace_experiment_plans(conn, project.id, project.experiment_plans)
        self._replace_payloads(conn, "hypotheses", project.id, project.hypotheses)
        self._replace_payloads(conn, "tasks", project.id, project.tasks)
        self._replace_payloads(conn, "source_collections", project.id, project.source_collections)
        self._replace_payloads(conn, "annotations", project.id, project.annotations)
        reports = list(project.quality_reports)
        for brief in project.briefs:
            if brief.quality_report and all(report.id != brief.quality_report.id for report in reports):
                reports.append(brief.quality_report)
        self._replace_payloads(conn, "quality_reports", project.id, reports)
        self._replace_agent_runs(conn, project.id, getattr(project, "agent_runs", []))
        self._replace_autonomous_artifacts(conn, project)
        conn.execute("delete from uploaded_papers where project_id = ?", (project.id,))
        conn.execute("delete from document_chunks where project_id = ?", (project.id,))
        conn.execute("delete from ingestion_runs where project_id = ?", (project.id,))
        conn.execute("delete from extracted_artifacts where project_id = ?", (project.id,))
        for paper in project.uploaded_papers:
            self._save_uploaded_paper(conn, project.id, paper)

    def _assemble_project(self, conn: sqlite3.Connection, project_id: str) -> ResearchProject:
        row = conn.execute("select payload from projects where id = ?", (project_id,)).fetchone()
        project = ResearchProject.model_validate(json.loads(row["payload"]))
        normalized_count = self._artifact_count(conn, project_id)
        if normalized_count == 0:
            self._save_project(conn, project)
            normalized_count = self._artifact_count(conn, project_id)
        if normalized_count:
            project.questions = self._list_payloads(conn, "questions", project_id, ResearchQuestion)
            project.briefs = self._list_payloads(conn, "briefs", project_id, ResearchBrief)
            project.memory = self._list_payloads(conn, "memory", project_id, MemoryItem)
            project.experiment_plans = self._list_payloads(conn, "experiment_plans", project_id, ExperimentPlan)
            project.hypotheses = self._list_payloads(conn, "hypotheses", project_id, HypothesisCandidate)
            project.tasks = self._list_payloads(conn, "tasks", project_id, ResearchTask)
            project.source_collections = self._list_payloads(conn, "source_collections", project_id, SourceCollection)
            project.annotations = self._list_payloads(conn, "annotations", project_id, ResearchAnnotation)
            project.uploaded_papers = self._list_uploaded_papers(conn, project_id)
            project.agent_runs = self._list_agent_runs(conn, project_id)
            project.quality_reports = self._list_payloads(conn, "quality_reports", project_id, EvidenceQualityReport)
            project.autonomous_agents = self._list_payloads(conn, "autonomous_agents", project_id, AgentDefinition)
            project.autonomous_agent_runs = self._list_agent_run_records(conn, project_id)
            project.saved_searches = self._list_payloads(conn, "saved_searches", project_id, SavedSearch)
            project.notifications = self._list_payloads(conn, "notifications", project_id, NotificationRecord)
            project.execution_artifacts = self._list_payloads(conn, "execution_artifacts", project_id, ExecutionArtifact)
        return project

    def _artifact_count(self, conn: sqlite3.Connection, project_id: str) -> int:
        tables = [
            "questions",
            "briefs",
            "memory",
            "experiment_plans",
            "hypotheses",
            "tasks",
            "source_collections",
            "annotations",
            "uploaded_papers",
            "agent_runs",
            "quality_reports",
            "extracted_artifacts",
            "autonomous_agents",
            "autonomous_agent_runs",
            "agent_decisions",
            "saved_searches",
            "notifications",
            "execution_artifacts",
        ]
        return sum(conn.execute(f"select count(*) as count from {table} where project_id = ?", (project_id,)).fetchone()["count"] for table in tables)

    def _replace_payloads(self, conn: sqlite3.Connection, table: str, project_id: str, items: Iterable[BaseModel]) -> None:
        conn.execute(f"delete from {table} where project_id = ?", (project_id,))
        for item in items:
            created_at = getattr(item, "created_at", "")
            self._insert_payload(conn, table, item.id, project_id, created_at, item)

    def _replace_experiment_plans(self, conn: sqlite3.Connection, project_id: str, items: Iterable[ExperimentPlan]) -> None:
        conn.execute("delete from experiment_plans where project_id = ?", (project_id,))
        for plan in items:
            conn.execute(
                """
                insert into experiment_plans
                (id, project_id, hypothesis_id, status, title, datasets, baselines, metrics, ablation_config, validation_plan, generated_script, created_at, payload)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    project_id = excluded.project_id,
                    hypothesis_id = excluded.hypothesis_id,
                    status = excluded.status,
                    title = excluded.title,
                    datasets = excluded.datasets,
                    baselines = excluded.baselines,
                    metrics = excluded.metrics,
                    ablation_config = excluded.ablation_config,
                    validation_plan = excluded.validation_plan,
                    generated_script = excluded.generated_script,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    plan.id,
                    project_id,
                    plan.hypothesis_id,
                    plan.status,
                    plan.title,
                    json.dumps([_model_or_value(item) for item in plan.datasets]),
                    json.dumps([_model_or_value(item) for item in plan.baselines]),
                    json.dumps([_model_or_value(item) for item in plan.metrics]),
                    json.dumps(plan.ablation_config.model_dump(mode="json")),
                    json.dumps(plan.validation_plan.model_dump(mode="json")),
                    plan.generated_script,
                    plan.created_at,
                    _dump(plan),
                ),
            )

    def _insert_payload(self, conn: sqlite3.Connection, table: str, item_id: str, project_id: str, created_at: str, item: BaseModel) -> None:
        conn.execute(
            f"""
            insert into {table} (id, project_id, created_at, payload)
            values (?, ?, ?, ?)
            on conflict(id) do update set
                project_id = excluded.project_id,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (item_id, project_id, created_at, _dump(item)),
        )

    def _list_payloads(self, conn: sqlite3.Connection, table: str, project_id: str, model: type[ModelT]) -> list[ModelT]:
        rows = conn.execute(
            f"select payload from {table} where project_id = ? order by created_at desc",
            (project_id,),
        ).fetchall()
        return [model.model_validate(json.loads(row["payload"])) for row in rows]

    def _save_uploaded_paper(self, conn: sqlite3.Connection, project_id: str, paper: UploadedPaper) -> None:
        conn.execute(
            """
            insert into uploaded_papers
            (id, project_id, title, filename, source_type, status, page_count, chunk_count, created_at, payload)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
                title = excluded.title,
                filename = excluded.filename,
                source_type = excluded.source_type,
                status = excluded.status,
                page_count = excluded.page_count,
                chunk_count = excluded.chunk_count,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (
                paper.id,
                project_id,
                paper.title,
                paper.filename,
                paper.source_type,
                paper.status,
                paper.page_count,
                paper.chunk_count,
                paper.created_at,
                _dump(paper),
            ),
        )
        conn.execute("delete from document_chunks where project_id = ? and paper_id = ?", (project_id, paper.id))
        conn.execute("delete from ingestion_runs where project_id = ? and paper_id = ?", (project_id, paper.id))
        conn.execute("delete from extracted_artifacts where project_id = ? and paper_id = ?", (project_id, paper.id))
        for chunk in paper.chunks:
            conn.execute(
                """
                insert into document_chunks (id, paper_id, project_id, page_number, created_at, text, payload)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (chunk.id, paper.id, project_id, chunk.page_number, chunk.created_at, chunk.text, _dump(chunk)),
            )
        for run in paper.ingestion_runs:
            conn.execute(
                """
                insert into ingestion_runs
                (id, paper_id, project_id, status, message, pages_extracted, chunks_created, created_at, payload)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    paper.id,
                    project_id,
                    run.status,
                    run.message,
                    run.pages_extracted,
                    run.chunks_created,
                    run.created_at,
                    _dump(run),
                ),
            )
        for artifact in paper.extractions.all_items():
            self._save_extraction_artifact(conn, project_id, artifact)

    def _list_uploaded_papers(self, conn: sqlite3.Connection, project_id: str) -> list[UploadedPaper]:
        rows = conn.execute(
            "select payload from uploaded_papers where project_id = ? order by created_at desc",
            (project_id,),
        ).fetchall()
        papers = [UploadedPaper.model_validate(json.loads(row["payload"])) for row in rows]
        for paper in papers:
            paper.chunks = self._list_chunks(conn, project_id, paper.id)
            paper.ingestion_runs = self._list_ingestion_runs(conn, project_id, paper.id)
            paper.extractions = _extraction_set_from_artifacts(self._list_extraction_artifacts(conn, project_id, paper.id))
        return papers

    def _list_chunks(self, conn: sqlite3.Connection, project_id: str, paper_id: str) -> list[DocumentChunk]:
        rows = conn.execute(
            """
            select payload, id, paper_id, page_number, text, created_at from document_chunks
            where project_id = ? and paper_id = ?
            order by page_number, created_at
            """,
            (project_id, paper_id),
        ).fetchall()
        return [_load_chunk(row) for row in rows]

    def _list_ingestion_runs(self, conn: sqlite3.Connection, project_id: str, paper_id: str) -> list[IngestionRun]:
        rows = conn.execute(
            """
            select payload, id, paper_id, status, message, pages_extracted, chunks_created, created_at
            from ingestion_runs
            where project_id = ? and paper_id = ?
            order by created_at desc
            """,
            (project_id, paper_id),
        ).fetchall()
        return [_load_ingestion_run(row) for row in rows]

    def _replace_agent_runs(self, conn: sqlite3.Connection, project_id: str, runs: Iterable[AgentRun]) -> None:
        conn.execute("delete from agent_runs where project_id = ?", (project_id,))
        for run in runs:
            conn.execute(
                """
                insert into agent_runs (id, project_id, question_id, status, started_at, completed_at, provider, payload)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run.id, project_id, run.question_id, run.status, run.started_at, run.completed_at, run.provider, _dump(run)),
            )

    def _list_agent_runs(self, conn: sqlite3.Connection, project_id: str) -> list[AgentRun]:
        rows = conn.execute(
            "select payload from agent_runs where project_id = ? order by started_at desc",
            (project_id,),
        ).fetchall()
        return [AgentRun.model_validate(json.loads(row["payload"])) for row in rows]

    def _replace_autonomous_artifacts(self, conn: sqlite3.Connection, project: ResearchProject) -> None:
        project_id = project.id
        for table in ["autonomous_agents", "autonomous_agent_runs", "agent_decisions", "saved_searches", "notifications", "execution_artifacts"]:
            conn.execute(f"delete from {table} where project_id = ?", (project_id,))
        for agent in project.autonomous_agents:
            conn.execute(
                """
                insert into autonomous_agents (id, project_id, type, status, created_at, payload)
                values (?, ?, ?, ?, ?, ?)
                """,
                (agent.id, project_id, agent.type, agent.status, agent.created_at, _dump(agent)),
            )
        for run in project.autonomous_agent_runs:
            conn.execute(
                """
                insert into autonomous_agent_runs
                (id, project_id, agent_id, status, current_step, created_at, completed_at, payload)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run.id, project_id, run.agent_id, run.status, run.current_step, run.created_at, run.completed_at, _dump(run)),
            )
            for decision in run.decisions:
                conn.execute(
                    """
                    insert into agent_decisions
                    (id, project_id, agent_id, run_id, action, created_at, payload)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (decision.id, project_id, decision.agent_id, decision.run_id, decision.action, decision.created_at, _dump(decision)),
                )
        for search in project.saved_searches:
            conn.execute(
                """
                insert into saved_searches (id, project_id, query, cadence, created_at, payload)
                values (?, ?, ?, ?, ?, ?)
                """,
                (search.id, project_id, search.query, search.cadence, search.created_at, _dump(search)),
            )
        for notification in project.notifications:
            conn.execute(
                """
                insert into notifications (id, project_id, status, created_at, payload)
                values (?, ?, ?, ?, ?)
                """,
                (notification.id, project_id, notification.status, notification.created_at, _dump(notification)),
            )
        for artifact in project.execution_artifacts:
            conn.execute(
                """
                insert into execution_artifacts (id, project_id, run_id, kind, created_at, payload)
                values (?, ?, ?, ?, ?, ?)
                """,
                (artifact.id, project_id, artifact.run_id, artifact.kind, artifact.created_at, _dump(artifact)),
            )

    def _list_agent_run_records(self, conn: sqlite3.Connection, project_id: str) -> list[AgentRunRecord]:
        runs = self._list_payloads(conn, "autonomous_agent_runs", project_id, AgentRunRecord)
        decisions_by_run: dict[str, list[AgentDecision]] = {}
        rows = conn.execute(
            "select payload from agent_decisions where project_id = ? order by created_at",
            (project_id,),
        ).fetchall()
        for row in rows:
            decision = AgentDecision.model_validate(json.loads(row["payload"]))
            decisions_by_run.setdefault(decision.run_id, []).append(decision)
        for run in runs:
            if decisions_by_run.get(run.id):
                run.decisions = decisions_by_run[run.id]
        return runs

    def _save_extraction_artifact(self, conn: sqlite3.Connection, project_id: str, artifact: ExtractionArtifact) -> None:
        conn.execute(
            """
            insert into extracted_artifacts (id, project_id, paper_id, source_id, kind, created_at, payload)
            values (?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
                project_id = excluded.project_id,
                paper_id = excluded.paper_id,
                source_id = excluded.source_id,
                kind = excluded.kind,
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (artifact.id, project_id, artifact.paper_id, artifact.source_id, artifact.kind, artifact.created_at, _dump(artifact)),
        )

    def _list_extraction_artifacts(self, conn: sqlite3.Connection, project_id: str, paper_id: str) -> list[ExtractionArtifact]:
        rows = conn.execute(
            """
            select payload from extracted_artifacts
            where project_id = ? and paper_id = ?
            order by created_at
            """,
            (project_id, paper_id),
        ).fetchall()
        return [_load_extraction_artifact(json.loads(row["payload"])) for row in rows]

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column_definition: str) -> None:
        column = column_definition.split()[0]
        columns = {row["name"] for row in conn.execute(f"pragma table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"alter table {table} add column {column_definition}")

    def _insert_global_payload(self, conn: sqlite3.Connection, table: str, item_id: str, created_at: str, item: BaseModel) -> None:
        conn.execute(
            f"""
            insert into {table} (id, created_at, payload)
            values (?, ?, ?)
            on conflict(id) do update set
                created_at = excluded.created_at,
                payload = excluded.payload
            """,
            (item_id, created_at, _dump(item)),
        )


def _dump(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"))


def _model_or_value(item):
    return item.model_dump(mode="json") if isinstance(item, BaseModel) else item


def _load_chunk(row: sqlite3.Row) -> DocumentChunk:
    if row["payload"]:
        return DocumentChunk.model_validate(json.loads(row["payload"]))
    return DocumentChunk(
        id=row["id"],
        paper_id=row["paper_id"],
        page_number=row["page_number"],
        text=row["text"],
        created_at=row["created_at"] or "",
    )


def _load_ingestion_run(row: sqlite3.Row) -> IngestionRun:
    if row["payload"]:
        return IngestionRun.model_validate(json.loads(row["payload"]))
    return IngestionRun(
        id=row["id"],
        paper_id=row["paper_id"],
        status=row["status"],
        message=row["message"],
        pages_extracted=row["pages_extracted"],
        chunks_created=row["chunks_created"],
        created_at=row["created_at"],
    )


def _load_extraction_artifact(payload: dict) -> ExtractionArtifact:
    models = {
        "claim": ExtractedClaim,
        "method": MethodologyItem,
        "dataset": DatasetMention,
        "metric": MetricMention,
        "baseline": BaselineMention,
        "limitation": LimitationItem,
        "future_work": FutureWorkItem,
        "assumption": AssumptionItem,
    }
    return models.get(payload.get("kind"), ExtractedClaim).model_validate(payload)


def _extraction_set_from_artifacts(artifacts: list[ExtractionArtifact]) -> PaperExtractionSet:
    extraction_set = PaperExtractionSet()
    for artifact in artifacts:
        if artifact.kind == "claim":
            extraction_set.claims.append(artifact)
        elif artifact.kind == "method":
            extraction_set.methods.append(artifact)
        elif artifact.kind == "dataset":
            extraction_set.datasets.append(artifact)
        elif artifact.kind == "metric":
            extraction_set.metrics.append(artifact)
        elif artifact.kind == "baseline":
            extraction_set.baselines.append(artifact)
        elif artifact.kind == "limitation":
            extraction_set.limitations.append(artifact)
        elif artifact.kind == "future_work":
            extraction_set.future_work.append(artifact)
        elif artifact.kind == "assumption":
            extraction_set.assumptions.append(artifact)
    return extraction_set
