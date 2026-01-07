from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text


def normalize_tenant_slug(x_tenant_slug: str | None) -> str:
    slug = (x_tenant_slug or "").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="X-Tenant-Slug header is required")
    return slug


def get_tenant_id(engine, slug: str) -> str:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": slug},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")

    return str(row["id"])
