from __future__ import annotations

from fastapi import Header, HTTPException
from sqlalchemy import text

from app.db import get_engine


def require_tenant(engine=None, x_tenant_slug: str | None = Header(default=None)) -> str:
    """
    Resolve tenant_id from header X-Tenant-Slug.

    Returns:
        tenant_id as UUID string

    Raises:
        HTTPException 400 if header missing
        HTTPException 404 if tenant slug not found
    """
    slug = (x_tenant_slug or "").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Slug header")

    if engine is None:
        engine = get_engine()

    with engine.begin() as conn:
        tenant_id = conn.execute(
            text(
                """
                SELECT id::text
                FROM tenants
                WHERE slug = :slug
                """
            ),
            {"slug": slug},
        ).scalar_one_or_none()

    if not tenant_id:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")

    return str(tenant_id)
