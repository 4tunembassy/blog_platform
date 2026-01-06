@'
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

# -------------------------------------------------------------------
# ENV LOADING (MUST RUN BEFORE importing app.db / anything that reads env)
# Always load backend/api/.env no matter where uvicorn is launched from.
# backend/api/app/main.py -> parents[1] == backend/api
# -------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

from fastapi import FastAPI, HTTPException  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import get_engine, db_ping  # noqa: E402
from app.schemas import ContentCreateIn, ContentOut, TransitionIn, EventOut  # noqa: E402
from app import repo  # noqa: E402
from app.workflow import validate_transition, WorkflowError, allowed_transitions, list_states  # noqa: E402
from app.tenant import require_tenant  # noqa: E402

app = FastAPI(title="Blog Platform API", version="0.3.0")


# -----------------------------
# Debug endpoints (TEMPORARY)
# -----------------------------
@app.get("/debug/fingerprint")
def debug_fingerprint():
    return {
        "file": __file__,
        "cwd": os.getcwd(),
        "time": datetime.now(timezone.utc).isoformat(),
        "env_path": str(ENV_PATH),
        "version": app.version,
    }


@app.get("/debug/dburl")
def debug_dburl():
    return {"DATABASE_URL": os.getenv("DATABASE_URL"), "ENV_PATH": str(ENV_PATH)}


@app.get("/debug/dbinfo")
def debug_dbinfo():
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  current_user AS user,
                  current_database() AS db,
                  current_schema() AS schema,
                  inet_server_addr() AS server_ip,
                  inet_server_port() AS server_port,
                  version() AS version
                """
            )
        ).mappings().first()

        tables = conn.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
        ).scalars().all()

    return {"conn": dict(row), "public_tables": tables}


# -----------------------------
# Health checks
# -----------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    engine = get_engine()
    db_ping(engine)
    return {"status": "ready", "db": "ok"}


# -----------------------------
# Workflow helpers (Step 3)
# -----------------------------
@app.get("/workflow/states")
def workflow_states():
    return {"states": list_states()}


@app.get("/content/{content_id}/allowed")
def content_allowed(content_id: str):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        current = repo.get_content(engine, tenant_id, content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")

    from_state = current["state"]
    risk_tier = int(current["risk_tier"])

    return {
        "content_id": content_id,
        "from_state": from_state,
        "risk_tier": risk_tier,
        "allowed": allowed_transitions(from_state, risk_tier),
    }


# -----------------------------
# Content workflow endpoints
# -----------------------------
@app.post("/content", response_model=ContentOut)
def create_content(body: ContentCreateIn):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        item = repo.create_content(
            engine,
            tenant_id=tenant_id,
            title=body.title,
            risk_tier=body.risk_tier,
        )

        repo.append_event(
            engine,
            tenant_id=tenant_id,
            entity_type="content",
            entity_id=item["id"],
            event_type="content.created",
            actor_type="system",
            actor_id=None,
            payload={
                "title": body.title,
                "risk_tier": body.risk_tier,
                "state": item.get("state"),
                "tenant_slug": "default",
            },
        )
        return item

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content/{content_id}", response_model=ContentOut)
def get_content(content_id: str):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        return repo.get_content(engine, tenant_id, content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")


@app.get("/content/{content_id}/events", response_model=list[EventOut])
def get_content_events(content_id: str):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        _ = repo.get_content(engine, tenant_id, content_id)
        return repo.list_events(engine, tenant_id, "content", content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")


@app.post("/content/{content_id}/transition", response_model=ContentOut)
def transition(content_id: str, body: TransitionIn):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        current = repo.get_content(engine, tenant_id, content_id)
        from_state = current["state"]
        risk_tier = int(current["risk_tier"])

        validate_transition(from_state, body.to_state, risk_tier)

        updated = repo.transition_content(engine, tenant_id, content_id, body.to_state)

        repo.append_event(
            engine,
            tenant_id=tenant_id,
            entity_type="content",
            entity_id=content_id,
            event_type="content.transition",
            actor_type=body.actor_type,
            actor_id=body.actor_id,
            payload={
                "from_state": from_state,
                "to_state": body.to_state,
                "reason": body.reason,
                "risk_tier": risk_tier,
                "tenant_slug": "default",
            },
        )
        return updated

    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
'@ | Set-Content -Encoding utf8 .\backend\api\app\main.py
