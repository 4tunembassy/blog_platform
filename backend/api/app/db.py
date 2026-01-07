import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from dotenv import load_dotenv


def _load_env() -> None:
    """
    Ensure .env is loaded even when uvicorn is started manually
    from different working directories.
    """
    # Try current working dir first (where uvicorn was launched)
    load_dotenv(override=False)

    # Try repo-known location: backend/api/.env (relative to this file)
    here = os.path.dirname(os.path.abspath(__file__))
    api_root = os.path.abspath(os.path.join(here, ".."))  # backend/api
    env_path = os.path.join(api_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    _load_env()

    dburl = os.getenv("DATABASE_URL")
    if not dburl:
        raise RuntimeError("DATABASE_URL is not set")

    echo = os.getenv("DB_ECHO", "false").lower() == "true"

    # psycopg3 + SQLAlchemy URL is expected: postgresql+psycopg://...
    return create_engine(dburl, echo=echo, future=True, pool_pre_ping=True)
