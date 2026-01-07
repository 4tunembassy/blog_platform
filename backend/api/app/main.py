import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Query
from dotenv import load_dotenv

from app.db import get_engine
from app.tenant import require_tenant, resolve_tenant_id
from app.schemas import (
    ContentCreateIn,
    ContentOut,
    ContentListOut,
    AllowedTransitionsOut,
    EventOut,
    TransitionIn,
    TransitionOut,
)
from app.repo import (
    create_content_item,
    insert_event,
    list_events,
    get_allowed_transitions,
    get_content,
    list_content,
    get_content_by_id,
    update_content_state,
)

# ---- ensure .env is loaded in ALL run modes ----
# Loads: backend/api/.env (relative to this file)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(override=False)
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH, override=False)

app = FastAPI(title="Blog Platform API", version="0.5.1")


# ---------- health/debug ----------

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("SELECT 1")
    return {"ready": True}


@app.get("/debug/fingerprint")
def debug_fingerprint():
    here = os.path.abspath(__file__)
    cwd = os.getcwd()
    return {
        "file": here,
        "cwd": cwd,
        "time": datetime.now(timezone.utc).isoformat(),
        "env_path": ENV_PATH,
        "version": app.version,
    }


@app.get("/debug/dburl")
def debug_dburl():
    dburl = os.getenv("DATABASE_URL")
    return {"DATABASE_URL_set": bool(dburl), "DATABASE_URL": dburl}


@app.get("/debug/dbinfo")
def debug_dbinfo():
    engine = get_engine()
    with engine.begin() as conn:
        ver = conn.exec_driver_sql("SELECT version()").scalar()
        now = conn.exec_driver_sql("SELECT now()").scalar()
    return {"version": ver, "now": str(now)}


# ---------- workflow ----------

@app.get("/workflow/states")
def workflow_states():
    return {"states": ["INGESTED", "CLASSIFIED", "DEFERRED", "RETIRED"], "policy": "v0"}


# ---------- content endpoints ----------

@app.post("/content", response_model=ContentOut)
def create_content_api(body: ContentCreateIn, x_tenant_slug: str = Depends(require_tenant)):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    item = create_content_item(engine, tenant_id, body.title, body.risk_tier)

    # event
    with engine.begin() as conn:
        insert_event(
            conn,
            tenant_id=tenant_id,
            entity_type="content",
            entity_id=item["id"],
            event_type="content.created",
            payload={
                "state": item["state"],
                "title": item["title"],
                "risk_tier": item["risk_tier"],
                "tenant_slug": x_tenant_slug,
            },
        )

    return item


@app.get("/content/{content_id}", response_model=ContentOut)
def get_content_api(content_id: UUID, x_tenant_slug: str = Depends(require_tenant)):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    item = get_content(engine, tenant_id, content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


# ✅ THIS IS THE ROUTE YOU’RE MISSING (GET /content)
@app.get("/content", response_model=ContentListOut)
def list_content_api(
    x_tenant_slug: str = Depends(require_tenant),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: str = Query(None, description="INGESTED/CLASSIFIED/DEFERRED/RETIRED"),
    risk_tier: int = Query(None, ge=1, le=3),
    q: str = Query(None, description="Title search"),
    sort: str = Query("created_at_desc", description="created_at_desc|created_at_asc|updated_at_desc|updated_at_asc"),
):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    items, total = list_content(
        engine,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        state=state,
        risk_tier=risk_tier,
        q=q,
        sort=sort,
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@app.get("/content/{content_id}/events", response_model=list[EventOut])
def content_events(content_id: UUID, x_tenant_slug: str = Depends(require_tenant)):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)
    return list_events(engine, tenant_id, "content", content_id)


@app.get("/content/{content_id}/allowed", response_model=AllowedTransitionsOut)
def allowed_transitions(content_id: UUID, x_tenant_slug: str = Depends(require_tenant)):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    row = get_allowed_transitions(engine, tenant_id, content_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return row


@app.post("/content/{content_id}/transition", response_model=TransitionOut)
def transition_content(content_id: UUID, body: TransitionIn, x_tenant_slug: str = Depends(require_tenant)):
    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, x_tenant_slug)

    with engine.begin() as conn:
        item = get_content_by_id(conn, tenant_id, content_id)
        if not item:
            raise HTTPException(status_code=404, detail="Content not found")
        from_state = item["state"]
        risk_tier = int(item["risk_tier"])

    allowed_row = get_allowed_transitions(engine, tenant_id, content_id)
    if not allowed_row:
        raise HTTPException(status_code=404, detail="Content not found")

    allowed = allowed_row["allowed"]
    if body.to_state not in allowed:
        raise HTTPException(
            status_code=409,
            detail={"message": "Transition not allowed", "from_state": from_state, "to_state": body.to_state, "allowed": allowed},
        )

    with engine.begin() as conn:
        update_content_state(conn, tenant_id, content_id, body.to_state)
        insert_event(
            conn,
            tenant_id=tenant_id,
            entity_type="content",
            entity_id=str(content_id),
            event_type="content.transitioned",
            payload={"from_state": from_state, "to_state": body.to_state, "risk_tier": risk_tier, "tenant_slug": x_tenant_slug},
        )

    return {"content_id": str(content_id), "from_state": from_state, "to_state": body.to_state, "risk_tier": risk_tier}
