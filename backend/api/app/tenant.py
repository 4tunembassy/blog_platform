# backend/api/app/tenant.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from fastapi import HTTPException


def resolve_tenant_id(engine: Engine, tenant_slug: str) -> str:
    sql = text("SELECT id::text AS id FROM public.tenants WHERE slug = :slug")
    with engine.begin() as conn:
        row = conn.execute(sql, {"slug": tenant_slug}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tenant not found for slug: {tenant_slug}")
    return row["id"]
