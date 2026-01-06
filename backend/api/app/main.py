from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

# Always load backend/api/.env, regardless of where uvicorn is launched from.
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"  # backend/api/.env
load_dotenv(dotenv_path=ENV_PATH, override=False)

from fastapi import FastAPI, HTTPException  # noqa: E402

from app.db import get_engine, db_ping  # noqa: E402
from app.schemas import ContentCreateIn, ContentOut, TransitionIn, EventOut, AllowedTransitionsOut  # noqa: E402
from app import repo  # noqa: E402
from app.workflow import validate_transition, allowed_transitions, WorkflowError, STATES  # noqa: E402
from app.tenant import require_tenant  # noqa: E402

app = FastAPI(title="Blog Platform API", version="0.3.0")

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

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    engine = get_engine()
    db_ping(engine)
    return {"status": "ready", "db": "ok"}

@app.get("/workflow/states")
def workflow_states():
    return {"states": STATES}

@app.get("/content/{content_id}/allowed", response_model=AllowedTransitionsOut)
def get_allowed(content_id: str):
    engine = get_engine()
    tenant_id = require_tenant(engine)
    try:
        current = repo.get_content(engine, tenant_id, content_id)
        from_state = current["state"]
        risk_tier = int(current["risk_tier"])
        return {
            "content_id": content_id,
            "from_state": from_state,
            "risk_tier": risk_tier,
            "allowed": allowed_transitions(from_state, risk_tier),
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")

@app.post("/content", response_model=ContentOut)
def create_content(body: ContentCreateIn):
    engine = get_engine()
    tenant_id = require_tenant(engine)

    try:
        item = repo.create_content(engine, tenant_id=tenant_id, title=body.title, risk_tier=body.risk_tier)
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
