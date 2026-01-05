from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

from fastapi import FastAPI, HTTPException, Header  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import get_engine, db_ping  # noqa: E402
from app.schemas import ContentCreateIn, ContentOut, TransitionIn, EventOut  # noqa: E402
from app import repo  # noqa: E402
from app.workflow import validate_transition, WorkflowError  # noqa: E402

app = FastAPI(title="Blog Platform API", version="0.2.6")
TENANT_HEADER = "X-Tenant-Slug"

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

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    engine = get_engine()
    db_ping(engine)
    return {"status": "ready", "db": "ok"}

@app.post("/content", response_model=ContentOut)
def create_content(
    body: ContentCreateIn,
    x_tenant_slug: str = Header(default="default", alias=TENANT_HEADER),
):
    engine = get_engine()
    try:
        tenant_id = repo.resolve_tenant_id(engine, x_tenant_slug)
        if not tenant_id:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")

        item = repo.create_content(engine, tenant_id=tenant_id, title=body.title, risk_tier=body.risk_tier)

        repo.append_event(
            engine,
            tenant_id=tenant_id,
            content_id=item["id"],
            event_type="content.created",
            actor_type="system",
            actor_id=None,
            status="ok",
            details={
                "entity_type": "content",
                "entity_id": item["id"],
                "payload": {
                    "title": body.title,
                    "risk_tier": body.risk_tier,
                    "state": item.get("state"),
                    "tenant_slug": x_tenant_slug,
                },
            },
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content/{content_id}", response_model=ContentOut)
def get_content(
    content_id: str,
    x_tenant_slug: str = Header(default="default", alias=TENANT_HEADER),
):
    engine = get_engine()
    try:
        tenant_id = repo.resolve_tenant_id(engine, x_tenant_slug)
        if not tenant_id:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")
        return repo.get_content(engine, tenant_id=tenant_id, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content/{content_id}/events", response_model=list[EventOut])
def get_content_events(
    content_id: str,
    x_tenant_slug: str = Header(default="default", alias=TENANT_HEADER),
):
    engine = get_engine()
    try:
        tenant_id = repo.resolve_tenant_id(engine, x_tenant_slug)
        if not tenant_id:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")
        _ = repo.get_content(engine, tenant_id=tenant_id, content_id=content_id)
        return repo.list_events(engine, tenant_id=tenant_id, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/content/{content_id}/transition", response_model=ContentOut)
def transition(
    content_id: str,
    body: TransitionIn,
    x_tenant_slug: str = Header(default="default", alias=TENANT_HEADER),
):
    engine = get_engine()
    try:
        tenant_id = repo.resolve_tenant_id(engine, x_tenant_slug)
        if not tenant_id:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")

        current = repo.get_content(engine, tenant_id=tenant_id, content_id=content_id)
        from_state = current["state"]
        risk_tier = int(current["risk_tier"])

        validate_transition(engine, from_state, body.to_state, risk_tier)

        updated = repo.transition_content(engine, tenant_id=tenant_id, content_id=content_id, to_state=body.to_state)

        repo.append_event(
            engine,
            tenant_id=tenant_id,
            content_id=content_id,
            event_type="content.transition",
            actor_type=body.actor_type,
            actor_id=body.actor_id,
            status="ok",
            details={
                "entity_type": "content",
                "entity_id": content_id,
                "payload": {
                    "from_state": from_state,
                    "to_state": body.to_state,
                    "reason": body.reason,
                    "risk_tier": risk_tier,
                    "tenant_slug": x_tenant_slug,
                },
            },
        )
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
