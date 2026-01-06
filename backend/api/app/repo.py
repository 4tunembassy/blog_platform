from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------
# Content
# -----------------------------
def create_content(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> dict[str, Any]:
    risk = f"TIER_{int(risk_tier)}"

    sql = text(
        """
        INSERT INTO content_items (tenant_id, title, risk)
        VALUES (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier))
        RETURNING
          id::text AS id,
          title,
          state::text AS state,
          (CASE
            WHEN risk::text = 'TIER_1' THEN 1
            WHEN risk::text = 'TIER_2' THEN 2
            WHEN risk::text = 'TIER_3' THEN 3
            ELSE 1
          END) AS risk_tier,
          created_at,
          updated_at
        """
    )

    with engine.begin() as conn:
        row = conn.execute(sql, {"tenant_id": tenant_id, "title": title, "risk": risk}).mappings().first()

    if not row:
        raise RuntimeError("Failed to create content item")

    return dict(row)


def get_content(engine: Engine, tenant_id: str, content_id: str) -> dict[str, Any]:
    sql = text(
        """
        SELECT
          id::text AS id,
          title,
          state::text AS state,
          (CASE
            WHEN risk::text = 'TIER_1' THEN 1
            WHEN risk::text = 'TIER_2' THEN 2
            WHEN risk::text = 'TIER_3' THEN 3
            ELSE 1
          END) AS risk_tier,
          created_at,
          updated_at
        FROM content_items
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(sql, {"tenant_id": tenant_id, "content_id": content_id}).mappings().first()

    if not row:
        raise KeyError("Not found")

    return dict(row)


def transition_content(engine: Engine, tenant_id: str, content_id: str, to_state: str) -> dict[str, Any]:
    sql = text(
        """
        UPDATE content_items
        SET state = CAST(:to_state AS content_state)
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        RETURNING
          id::text AS id,
          title,
          state::text AS state,
          (CASE
            WHEN risk::text = 'TIER_1' THEN 1
            WHEN risk::text = 'TIER_2' THEN 2
            WHEN risk::text = 'TIER_3' THEN 3
            ELSE 1
          END) AS risk_tier,
          created_at,
          updated_at
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": tenant_id, "content_id": content_id, "to_state": to_state},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")

    return dict(row)


# -----------------------------
# Events table helpers
# -----------------------------
def append_event(
    engine: Engine,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict[str, Any],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    created_at = created_at or _utcnow()

    # CRITICAL FIX: dict -> JSON string
    payload_json = json.dumps(payload, ensure_ascii=False)

    sql = text(
        """
        INSERT INTO events (
          tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at
        )
        VALUES (
          CAST(:tenant_id AS uuid),
          :entity_type,
          CAST(:entity_id AS uuid),
          :event_type,
          :actor_type,
          :actor_id,
          CAST(:payload AS jsonb),
          :created_at
        )
        RETURNING
          id::text AS id,
          entity_type,
          entity_id::text AS entity_id,
          event_type,
          actor_type,
          actor_id,
          payload,
          created_at
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "payload": payload_json,
                "created_at": created_at,
            },
        ).mappings().first()

    if not row:
        raise RuntimeError("Failed to append event")

    return dict(row)


def list_events(engine: Engine, tenant_id: str, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT
          id::text AS id,
          entity_type,
          entity_id::text AS entity_id,
          event_type,
          actor_type,
          actor_id,
          payload,
          created_at
        FROM events
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND entity_type = :entity_type
          AND entity_id = CAST(:entity_id AS uuid)
        ORDER BY created_at DESC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
        ).mappings().all()

    return [dict(r) for r in rows]
