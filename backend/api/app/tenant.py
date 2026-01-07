from __future__ import annotations

from sqlalchemy import text


def resolve_tenant_id(engine, tenant_slug: str | None) -> str:
    """
    Resolve tenant_id (uuid string) from tenant slug.
    - If header missing/empty => 'default'
    - Raises KeyError if slug not found
    """
    slug = (tenant_slug or "default").strip()
    if not slug:
        slug = "default"

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id::text AS id FROM tenants WHERE slug = :slug"),
            {"slug": slug},
        ).mappings().first()

    if not row:
        raise KeyError(f"Unknown tenant slug: {slug}")

    return row["id"]
