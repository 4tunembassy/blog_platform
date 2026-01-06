from __future__ import annotations

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Alembic Config object
config = context.config

# -------------------------------------------------------------------
# ENV LOADING
# Always load backend/api/.env no matter where alembic is launched from.
# This file: backend/api/migrations/env.py
# parents[1] => backend/api
# -------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    from logging.config import fileConfig

    fileConfig(config.config_file_name)

# No ORM metadata in this project yet; we run explicit SQL in revisions.
target_metadata = None

def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(f"DATABASE_URL is not set. Expected it in {ENV_PATH}")
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
