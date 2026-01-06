from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Engine

def _now():
    return datetime.now(timezone.utc)

def get_tenant_id(engine: Engine, tenant_slug: str) -> str:
    with engine.begin() as conn:
        tid = conn.execute(
            text("SELECT id::text FROM tenants WHERE slug = :slug"),
            {"slug": tenant_slug},
        ).scalar_one_or_none()
    if not tid:
        raise KeyError(f"Tenant not found: {tenant_slug}")
    return tid

def _risk_enum_from_int(risk_tier: int) -> str:
    return f"TIER_{int(risk_tier)}"

def _risk_int_from_enum(risk_enum: str) -> int:
    try:
        return int(str(risk_enum).split("_")[1])
    except Exception:
        return 1

def create_content(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO content_items (tenant_id, title, risk)
                VALUES (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier))
                RETURNING
                  id::text AS id,
                  title AS title,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                """
            ),
            {"tenant_id": tenant_id, "title": title, "risk": _risk_enum_from_int(risk_tier)},
        ).mappings().one()

    return {
        "id": row["id"],
        "title": row["title"] or "",
        "state": row["state"],
        "risk_tier": _risk_int_from_enum(row["risk"]),
        "created_at": row["created_at"].isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].isoformat().replace("+00:00", "Z"),
    }

def get_content(engine: Engine, tenant_id: str, content_id: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  id::text AS id,
                  title AS title,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                FROM content_items
                WHERE id = CAST(:id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
                """
            ),
            {"id": content_id, "tenant_id": tenant_id},
        ).mappings().one_or_none()

    if not row:
        raise KeyError("Not found")

    return {
        "id": row["id"],
        "title": row["title"] or "",
        "state": row["state"],
        "risk_tier": _risk_int_from_enum(row["risk"]),
        "created_at": row["created_at"].isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].isoformat().replace("+00:00", "Z"),
    }

def transition_content(engine: Engine, tenant_id: str, content_id: str, to_state: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE content_items
                SET state = CAST(:to_state AS content_state)
                WHERE id = CAST(:id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
                RETURNING
                  id::text AS id,
                  title AS title,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                """
            ),
            {"id": content_id, "tenant_id": tenant_id, "to_state": to_state},
        ).mappings().one_or_none()

    if not row:
        raise KeyError("Not found")

    return {
        "id": row["id"],
        "title": row["title"] or "",
        "state": row["state"],
        "risk_tier": _risk_int_from_enum(row["risk"]),
        "created_at": row["created_at"].isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].isoformat().replace("+00:00", "Z"),
    }

def append_event(
    engine: Engine,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO provenance_events
                  (tenant_id, content_id, agent_name, status, details, created_at)
                VALUES
                  (CAST(:tenant_id AS uuid), CAST(:content_id AS uuid), :agent_name, :status, CAST(:details AS jsonb), :created_at)
                """
            ),
            {
                "tenant_id": tenant_id,
                "content_id": entity_id if entity_type == "content" else None,
                "agent_name": actor_type or "system",
                "status": event_type,
                "details": payload or {},
                "created_at": _now(),
            },
        )

def list_events(engine: Engine, tenant_id: str, entity_type: str, entity_id: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                  id::text AS id,
                  'content'::text AS entity_type,
                  content_id::text AS entity_id,
                  status AS event_type,
                  agent_name AS actor_type,
                  NULL::text AS actor_id,
                  details AS payload,
                  created_at
                FROM provenance_events
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND content_id = CAST(:content_id AS uuid)
                ORDER BY created_at DESC
                LIMIT 200
                """
            ),
            {"tenant_id": tenant_id, "content_id": entity_id},
        ).mappings().all()

    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "event_type": r["event_type"],
                "actor_type": r["actor_type"],
                "actor_id": r["actor_id"],
                "payload": dict(r["payload"] or {}),
                "created_at": r["created_at"].isoformat().replace("+00:00", "Z"),
            }
        )
    return out
