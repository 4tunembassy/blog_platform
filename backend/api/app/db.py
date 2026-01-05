from __future__ import annotations

import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url

def get_engine() -> Engine:
    db_echo = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes", "on")
    return create_engine(_get_database_url(), echo=db_echo, pool_pre_ping=True)

def db_ping(engine: Engine) -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
