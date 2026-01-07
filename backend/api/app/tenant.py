from fastapi import Header, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Engine


def require_tenant(x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug")) -> str:
    if not x_tenant_slug or not x_tenant_slug.strip():
        raise HTTPException(status_code=400, detail="X-Tenant-Slug header is required")
    return x_tenant_slug.strip()


def resolve_tenant_id(engine: Engine, tenant_slug: str) -> str:
    sql = text("""
        SELECT id::text AS id
        FROM public.tenants
        WHERE slug = :slug
        LIMIT 1
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"slug": tenant_slug}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_slug}")

    return row["id"]
