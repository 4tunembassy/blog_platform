# backend/api/app/db.py
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _load_env_once() -> None:
    """
    Loads .env from:
      1) ENV_PATH if provided
      2) backend/api/.env (project default)
      3) current working directory .env (fallback)
    """
    # 1) explicit ENV_PATH
    env_path = os.getenv("ENV_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            load_dotenv(p, override=False)
            return

    # 2) backend/api/.env (this file is backend/api/app/db.py)
    backend_api_dir = Path(__file__).resolve().parents[1]  # .../backend/api
    p2 = backend_api_dir / ".env"
    if p2.exists():
        load_dotenv(p2, override=False)
        return

    # 3) cwd .env
    p3 = Path.cwd() / ".env"
    if p3.exists():
        load_dotenv(p3, override=False)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine

    if _engine is not None:
        return _engine

    _load_env_once()

    db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not db_url:
        backend_api_dir = Path(__file__).resolve().parents[1]
        tried = [
            f"ENV_PATH={os.getenv('ENV_PATH')}",
            str(backend_api_dir / ".env"),
            str(Path.cwd() / ".env"),
        ]
        raise RuntimeError(
            "DATABASE_URL is not set. Ensure it exists in backend/api/.env or set ENV_PATH.\n"
            f"Tried: {', '.join(tried)}"
        )

    _engine = create_engine(db_url, pool_pre_ping=True, future=True)
    return _engine
