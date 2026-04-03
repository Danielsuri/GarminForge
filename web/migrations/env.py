from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path so web.* imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from alembic import context
from sqlalchemy import engine_from_config, pool

from web.db import DATABASE_URL, Base
import web.models  # noqa: F401 — registers all models with Base.metadata

target_metadata = Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
