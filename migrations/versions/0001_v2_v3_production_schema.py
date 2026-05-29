from __future__ import annotations

from alembic import op


revision = "0001_v2_v3_production_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from ai_scientist._pgsql_schema import PGSQL_SCHEMA_SQL

    op.execute(PGSQL_SCHEMA_SQL)


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
