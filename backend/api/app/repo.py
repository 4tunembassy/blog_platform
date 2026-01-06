from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text


def _risk_enum_from_int(risk_tier: int) -> str:
    # DB enum values are: TIER_1, TIER_2, ...
    # Input from API is integer: 1,2,3...
    if not isinstance(risk_tier, int):
        raise ValueError("risk_tier must be an integer")
    if risk_tier < 1 or risk_tier > 5:
        raise ValueError("risk_tier must be between 1 and 5")
    return f"TIER_{risk_tier}"


def create_content(engine, tenant_id: str, title: str, risk_tier: int):
    risk_enum = _risk_enum_from_int(risk_tier)

    with engine.begin() as conn:
        row = conn.execute(
            text(
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
                    WHEN risk::text = 'TIER_4' THEN 4
                    WHEN risk::text = 'TIER_5' THEN 5
                    ELSE 1
                  END) AS risk_tier,
                  created_at,
                  updated_at
                """
            ),
            {"tenant_id": tenant_id, "title": title, "risk": risk_enum},
        ).mappings().first()

    if not row:
        raise RuntimeError("Insert failed: content_items")
    return dict(row)


def get_content(engine, tenant_id: str, content_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  id::text AS id,
                  title,
                  state::text AS state,
                  (CASE
                    WHEN risk::text = 'TIER_1' THEN 1
                    WHEN risk::text = 'TIER_2' THEN 2
                    WHEN risk::text = 'TIER_3' THEN 3
                    WHEN risk::text = 'TIER_4' THEN 4
                    WHEN risk::text = 'TIER_5' THEN 5
                    ELSE 1
                  END) AS risk_tier,
                  created_at,
                  updated_at
                FROM content_items
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND id = CAST(:content_id AS uuid)
                """
            ),
            {"tenant_id": tenant_id, "content_id": content_id},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")
    return dict(row)


def transition_content(engine, tenant_id: str, content_id: str, to_state: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
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
                    WHEN risk::text = 'TIER_4' THEN 4
                    WHEN risk::text = 'TIER_5' THEN 5
                    ELSE 1
                  END) AS risk_tier,
                  created_at,
                  updated_at
                """
            ),
            {"tenant_id": tenant_id, "content_id": content_id, "to_state": to_state},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")
    return dict(row)


def append_event(
    engine,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict,
):
    """
    IMPORTANT:
    Psycopg3 cannot adapt a Python dict into jsonb when used via plain SQL/text placeholders.
    So we serialize payload to JSON string ourselves.
    """
    created_at = datetime.now(timezone.utc)
    payload_json = json.dumps(payload, ensure_ascii=False)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO events (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
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
                """
            ),
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
        )


def list_events(engine, tenant_id: str, entity_type: str, entity_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
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
            ),
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
        ).mappings().all()

    return [dict(r) for r in rows]
