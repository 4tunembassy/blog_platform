# backend/api/app/main.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.engine import Engine

from app.db import get_engine
from app.repo import (
    create_content_item,
    get_allowed_transitions,
    list_events_for_entity,
    ensure_core_tables_exist,
)
from app.tenant import resolve_tenant_id
from app.schemas import ContentCreateIn, ContentOut, AllowedTransitionOut, EventOut


APP_VERSION = "0.3.4"

app = FastAPI(title="Blog Platform API", version=APP_VERSION)


def require_tenant_slug(x_tenant_slug: Optional[str] = Header(default=None, alias="X-Tenant-Slug")) -> str:
    if not x_tenant_slug:
        raise HTTPException(status_code=400, detail="X-Tenant-Slug header is required")
    return x_tenant_slug


@app.on_event("startup")
def _startup() -> None:
    # Ensure minimal tables exist (safe idempotent)
    engine = get_engine()
    ensure_core_tables_exist(engine)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "version": APP_VERSION}


@app.get("/readyz")
def readyz() -> dict:
    # If DB connection fails, raise 503
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"ok": True, "db": "ok", "version": APP_VERSION}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not ready: {e}")


@app.get("/debug/fingerprint")
def debug_fingerprint() -> dict:
    return {
        "file": __file__,
        "cwd": os.getcwd(),
        "time": datetime.now(timezone.utc).isoformat(),
        "env_path": str((__import__("pathlib").Path(__file__).resolve().parents[1] / ".env")),
        "version": APP_VERSION,
    }


@app.get("/debug/dburl")
def debug_dburl() -> dict:
    # Never import app.settings. Just expose what db.py sees.
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    return {"DATABASE_URL_set": bool(url), "DATABASE_URL": url}


@app.get("/debug/dbinfo")
def debug_dbinfo() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        db = conn.exec_driver_sql("select current_database()").scalar()
        usr = conn.exec_driver_sql("select current_user").scalar()
        now = conn.exec_driver_sql("select now()").scalar()
    return {"database": db, "user": usr, "now": str(now)}


@app.get("/workflow/states")
def workflow_states() -> dict:
    # Keep simple; your policy engine can expand later
    return {"states": ["INGESTED", "CLASSIFIED", "DEFERRED", "RETIRED"]}


@app.post("/content", response_model=ContentOut)
def create_content(
    payload: ContentCreateIn,
    x_tenant_slug: str = Depends(require_tenant_slug),
) -> ContentOut:
    engine: Engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    now = datetime.now(timezone.utc)

    item = create_content_item(
        engine=engine,
        tenant_id=tenant_id,
        title=payload.title,
        risk_tier=payload.risk_tier,
        now=now,
        tenant_slug=x_tenant_slug,
    )

    # Ensure response is string timestamps to satisfy schema stability
    return ContentOut(
        id=item["id"],
        title=item["title"],
        state=item["state"],
        risk_tier=item["risk_tier"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


@app.get("/content/{content_id}/allowed", response_model=List[AllowedTransitionOut])
def allowed_transitions(
    content_id: UUID,
    x_tenant_slug: str = Depends(require_tenant_slug),
) -> List[AllowedTransitionOut]:
    engine: Engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)
    rows = get_allowed_transitions(engine, tenant_id, content_id)
    return [AllowedTransitionOut(**r) for r in rows]


@app.get("/content/{content_id}/events", response_model=List[EventOut])
def content_events(
    content_id: UUID,
    x_tenant_slug: str = Depends(require_tenant_slug),
) -> List[EventOut]:
    engine: Engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)
    rows = list_events_for_entity(engine, tenant_id, "content", content_id)
    return [EventOut(**r) for r in rows]
