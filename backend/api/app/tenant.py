from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text


def require_tenant(engine, x_tenant_slug: str | None) -> str:
    """
    Resolve tenant_id from header X-Tenant-Slug.

    IMPORTANT:
    - This is a plain function (not a FastAPI dependency).
    - main.py passes the header string explicitly.
    """
    slug = (x_tenant_slug or "").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="X-Tenant-Slug header is required")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id::text AS id
                FROM public.tenants
                WHERE slug = :slug
                LIMIT 1
                """
            ),
            {"slug": slug},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=400, detail=f"Unknown tenant slug: {slug}")

    return row["id"]
