from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _load_env_once() -> None:
    # Load .env located in backend/api/.env by default if present
    # (uvicorn working dir is backend/api)
    load_dotenv(override=False)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    _load_env_once()

    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    echo = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes", "y")
    # pool_pre_ping prevents stale sockets causing intermittent “Socket is not connected”
    return create_engine(db_url, echo=echo, pool_pre_ping=True, future=True)


def get_database_url_safe() -> dict:
    """
    Debug helper used by /debug/dburl
    """
    _load_env_once()
    db_url = os.getenv("DATABASE_URL", "").strip()
    return {
        "DATABASE_URL_set": bool(db_url),
        "DATABASE_URL": db_url if db_url else None,
    }
