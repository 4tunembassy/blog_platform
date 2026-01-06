@'
from __future__ import annotations

from fastapi import Header, HTTPException
from sqlalchemy import text


def require_tenant(engine, x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug")) -> str:
    """
    Resolves tenant_id from X-Tenant-Slug header.
    Returns tenant_id as UUID string.
    """
    if not x_tenant_slug:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Slug header")

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id::text AS id FROM tenants WHERE slug = :slug"),
            {"slug": x_tenant_slug},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_slug}")

    return row["id"]
'@ | Set-Content -Encoding utf8 .\backend\api\app\tenant.py
