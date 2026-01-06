from __future__ import annotations

from fastapi import Header, HTTPException
from sqlalchemy import text

from app.db import get_engine


def require_tenant(engine=None, x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug")) -> str:
    """
    Resolves tenant_id (uuid string) from X-Tenant-Slug header.
    Defaults to 'default' if header is missing/empty.
    """
    slug = (x_tenant_slug or "default").strip()
    if not slug:
        slug = "default"

    if engine is None:
        engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id::text AS id FROM tenants WHERE slug = :slug"),
            {"slug": slug},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown tenant slug: {slug}")

    return row["id"]
