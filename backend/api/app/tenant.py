from __future__ import annotations

from fastapi import Header, HTTPException
from sqlalchemy.engine import Engine

from app import repo

def require_tenant(engine: Engine, x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug")) -> str:
    if not x_tenant_slug:
        raise HTTPException(status_code=400, detail="Missing header: X-Tenant-Slug")
    try:
        return repo.get_tenant_id(engine, x_tenant_slug)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")
