from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

from ai_scientist.config import settings


def run_migrations_online() -> None:
    engine = create_engine(settings.database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
