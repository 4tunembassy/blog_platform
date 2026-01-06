from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


DEFAULT_TENANT_SLUG = "default"


def require_tenant(engine: Engine, x_tenant_slug: str | None) -> str:
    """
    Resolve tenant_id from the request header "X-Tenant-Slug".

    IMPORTANT:
    - This function MUST receive a plain string (or None).
    - Do NOT declare FastAPI Header() here because we call this directly from endpoints.
    """

    slug = (x_tenant_slug or DEFAULT_TENANT_SLUG).strip()
    if not slug:
        slug = DEFAULT_TENANT_SLUG

    sql = text(
        """
        SELECT id::text AS id
        FROM tenants
        WHERE slug = :slug
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(sql, {"slug": slug}).mappings().first()

    if not row:
        # If tenant doesn't exist, you can either throw or fallback.
        # We'll throw clearly to avoid silent bugs.
        raise KeyError(f"Tenant not found for slug '{slug}'")

    return str(row["id"])
