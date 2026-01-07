from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from app.db import get_database_url_safe, get_engine
from app.repo import (
    create_content_item,
    get_allowed_transitions,
    get_content_by_id,
    insert_event,
    list_content,
    list_events,
    transition_content,
)
from app.schemas import (
    AllowedTransitionsOut,
    ContentCreateIn,
    ContentListOut,
    ContentOut,
    EventOut,
    SortKey,
    TransitionIn,
    TransitionOut,
)
from app.tenant import resolve_tenant_id

app = FastAPI(title="Blog Platform API", version="0.4.0")


# -----------------------------
# Dependencies
# -----------------------------

def tenant_id_dep(x_tenant_slug: str = Header(default=None, alias="X-Tenant-Slug")) -> str:
    try:
        engine = get_engine()
        return resolve_tenant_id(engine, x_tenant_slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Health / Debug
# -----------------------------

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    # Light readiness check: engine creation only (fast), DB connectivity is exercised on first request
    _ = get_engine()
    return {"ready": True}


@app.get("/debug/dburl")
def debug_dburl():
    # No dependency on app.settings; always safe
    return JSONResponse(get_database_url_safe())


# -----------------------------
# Content
# -----------------------------

@app.post("/content", response_model=ContentOut)
def create_content(payload: ContentCreateIn, tenant_id: str = Depends(tenant_id_dep)):
    engine = get_engine()

    item = create_content_item(engine, tenant_id, payload.title, payload.risk_tier)

    insert_event(
        engine,
        tenant_id=tenant_id,
        entity_type="content",
        entity_id=item["id"],
        event_type="content.created",
        payload={
            "tenant_slug": "default",  # kept for now; later we can resolve actual slug
            "state": item["state"],
            "title": item["title"],
            "risk_tier": item["risk_tier"],
        },
        actor_type="system",
        actor_id=None,
    )

    return item


@app.get("/content", response_model=ContentListOut)
def get_content_list(
    tenant_id: str = Depends(tenant_id_dep),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: SortKey = Query(default="created_at_desc"),
    q: str | None = Query(default=None, min_length=1, max_length=200),
):
    engine = get_engine()
    items, total = list_content(engine, tenant_id, limit=limit, offset=offset, sort=sort, q=q)
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@app.get("/content/{content_id}", response_model=ContentOut)
def get_content_one(content_id: str, tenant_id: str = Depends(tenant_id_dep)):
    engine = get_engine()
    item = get_content_by_id(engine, tenant_id, content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not Found")
    return item


@app.get("/content/{content_id}/allowed", response_model=AllowedTransitionsOut)
def allowed_transitions(content_id: str, tenant_id: str = Depends(tenant_id_dep)):
    engine = get_engine()
    try:
        return get_allowed_transitions(engine, tenant_id, content_id)
    except ValueError as e:
        # content not found or invalid rule request
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="Not Found")
        raise HTTPException(status_code=400, detail=msg)


@app.post("/content/{content_id}/transition", response_model=TransitionOut)
def do_transition(content_id: str, payload: TransitionIn, tenant_id: str = Depends(tenant_id_dep)):
    engine = get_engine()
    try:
        result = transition_content(engine, tenant_id, content_id, payload.to_state)
    except ValueError as e:
        msg = str(e)
        if "not allowed" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="Not Found")
        raise HTTPException(status_code=400, detail=msg)

    insert_event(
        engine,
        tenant_id=tenant_id,
        entity_type="content",
        entity_id=content_id,
        event_type="content.transitioned",
        payload={
            "tenant_slug": "default",
            "from_state": result["from_state"],
            "to_state": result["to_state"],
            "risk_tier": result["risk_tier"],
        },
        actor_type="system",
        actor_id=None,
    )

    return result


@app.get("/content/{content_id}/events", response_model=list[EventOut])
def get_content_events(content_id: str, tenant_id: str = Depends(tenant_id_dep)):
    engine = get_engine()
    # If content does not exist, return 404 (optional strictness)
    item = get_content_by_id(engine, tenant_id, content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not Found")

    return list_events(engine, tenant_id, entity_type="content", entity_id=content_id)
