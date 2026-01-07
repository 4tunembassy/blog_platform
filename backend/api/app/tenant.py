from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def resolve_tenant_id(engine: Engine, tenant_slug: str) -> str:
    """
    Returns tenant_id as text UUID for a given slug, raises ValueError if not found.
    """
    slug = (tenant_slug or "").strip()
    if not slug:
        raise ValueError("X-Tenant-Slug header is required")

    sql = text(
        """
        SELECT id::text AS id
        FROM public.tenants
        WHERE slug = :slug
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(sql, {"slug": slug}).mappings().one_or_none()

    if not row:
        raise ValueError(f"Unknown tenant slug: {slug}")

    return row["id"]
