from __future__ import annotations

from ._pgsql_schema import PGSQL_SCHEMA_SQL
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


ALEMBIC_BOOTSTRAP_SQL = PGSQL_SCHEMA_SQL
