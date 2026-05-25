from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from pydantic import BaseModel

from .models import JobRecord, ObjectStorageRecord, SubscriptionRecord, Team, TeamMembership, TenantUser, UsageEvent
from .postgres_store import PostgresStore
from .storage import SQLiteStore

TABLES = [
    "projects",
    "questions",
    "briefs",
    "memory",
    "experiment_plans",
    "hypotheses",
    "tasks",
    "source_collections",
    "annotations",
    "uploaded_papers",
    "document_chunks",
    "ingestion_runs",
    "agent_runs",
    "quality_reports",
    "extracted_artifacts",
    "tenant_users",
    "teams",
    "team_memberships",
    "project_memberships",
    "usage_events",
    "subscriptions",
    "autonomous_agents",
    "autonomous_agent_runs",
    "agent_decisions",
    "saved_searches",
    "notifications",
    "execution_artifacts",
    "jobs",
    "object_storage_records",
]


def main() -> None:
    parser = argparse.ArgumentParser("ai_scientist.migrate")
    sub = parser.add_subparsers(dest="command", required=True)
    sqlite_to_postgres = sub.add_parser("sqlite-to-postgres")
    sqlite_to_postgres.add_argument("--sqlite", required=True)
    sqlite_to_postgres.add_argument("--database-url", required=True)
    sqlite_to_postgres.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "sqlite-to-postgres":
        summary = sqlite_to_postgres_summary(Path(args.sqlite), args.database_url, args.dry_run)
        print(json.dumps(summary, indent=2))


def sqlite_to_postgres_summary(sqlite_path: Path, database_url: str, dry_run: bool = False) -> dict:
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")
    counts = {}
    with sqlite3.connect(sqlite_path) as conn:
        for table in TABLES:
            try:
                counts[table] = conn.execute(f"select count(*) from {table}").fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
    migrated = {}
    if not dry_run:
        source = SQLiteStore(sqlite_path)
        target = PostgresStore(database_url)
        projects = source.list_projects()
        for project in projects:
            target.save_project(project)
        migrated["projects"] = len(projects)
        migrated["tenant_users"] = _migrate_global(sqlite_path, target, "tenant_users", TenantUser)
        migrated["teams"] = _migrate_global(sqlite_path, target, "teams", Team)
        migrated["team_memberships"] = _migrate_global(sqlite_path, target, "team_memberships", TeamMembership)
        migrated["subscriptions"] = _migrate_subscriptions(sqlite_path, target)
        migrated["usage_events"] = _migrate_usage_events(sqlite_path, target)
        migrated["jobs"] = _migrate_jobs(sqlite_path, target)
        migrated["object_storage_records"] = _migrate_objects(sqlite_path, target)
    return {
        "source": str(sqlite_path),
        "target": mask_url(database_url),
        "dry_run": dry_run,
        "status": "validated" if dry_run else "migrated",
        "table_counts": counts,
        "migrated": migrated,
    }


def _rows(sqlite_path: Path, table: str) -> list[dict]:
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in conn.execute(f"select payload from {table}").fetchall()]
        except sqlite3.OperationalError:
            return []


def _migrate_global(sqlite_path: Path, target: PostgresStore, table: str, model: type[BaseModel]) -> int:
    count = 0
    for row in _rows(sqlite_path, table):
        item = model.model_validate(json.loads(row["payload"]))
        target._upsert_global(table, item.id, getattr(item, "created_at", ""), item)
        count += 1
    return count


def _migrate_subscriptions(sqlite_path: Path, target: PostgresStore) -> int:
    count = 0
    for row in _rows(sqlite_path, "subscriptions"):
        item = SubscriptionRecord.model_validate(json.loads(row["payload"]))
        target._execute(
            """
            insert into subscriptions (id, team_id, tier, status, created_at, payload)
            values (%s, %s, %s, %s, %s, %s::jsonb)
            on conflict(id) do update set payload = excluded.payload
            """,
            (item.id, item.team_id, item.tier, item.status, item.created_at, json.dumps(item.model_dump(mode="json"))),
        )
        count += 1
    return count


def _migrate_usage_events(sqlite_path: Path, target: PostgresStore) -> int:
    count = 0
    for row in _rows(sqlite_path, "usage_events"):
        target.record_usage_event(UsageEvent.model_validate(json.loads(row["payload"])))
        count += 1
    return count


def _migrate_jobs(sqlite_path: Path, target: PostgresStore) -> int:
    count = 0
    for row in _rows(sqlite_path, "jobs"):
        target.save_job(JobRecord.model_validate(json.loads(row["payload"])))
        count += 1
    return count


def _migrate_objects(sqlite_path: Path, target: PostgresStore) -> int:
    count = 0
    for row in _rows(sqlite_path, "object_storage_records"):
        target.save_object_record(ObjectStorageRecord.model_validate(json.loads(row["payload"])))
        count += 1
    return count


def mask_url(value: str) -> str:
    if "@" not in value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    return f"{scheme}://***@{rest.split('@', 1)[1]}"


if __name__ == "__main__":
    main()
