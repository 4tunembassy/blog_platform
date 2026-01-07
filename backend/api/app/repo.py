from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


# ----------------------------
# helpers
# ----------------------------
def _utcnow():
    return datetime.now(timezone.utc)


def _risk_enum_from_int(risk_tier: int) -> str:
    """
    DB column: content_items.risk is enum risk_tier with values like 'TIER_1'
    API input: risk_tier is int 1..4 (or more)
    """
    try:
        n = int(risk_tier)
    except Exception:
        n = 1
    if n < 1:
        n = 1
    return f"TIER_{n}"


def _jsonb(value: Any) -> str:
    """
    IMPORTANT:
    We pass JSON as a string and CAST(:payload AS jsonb) in SQL.
    psycopg cannot adapt dict reliably for raw text() queries.
    """
    return json.dumps(value, ensure_ascii=False)


# ----------------------------
# content
# ----------------------------
def create_content(engine, tenant_id: str, title: str, risk_tier: int) -> dict:
    risk_enum = _risk_enum_from_int(risk_tier)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO public.content_items (tenant_id, title, risk)
                VALUES (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier))
                RETURNING
                    id::text AS id,
                    title,
                    state::text AS state,
                    risk::text AS risk,
                    created_at,
                    updated_at
                """
            ),
            {"tenant_id": tenant_id, "title": title, "risk": risk_enum},
        ).mappings().first()

    if not row:
        raise RuntimeError("Failed to create content row")

    # API expects risk_tier int; we keep your response contract stable.
    # Convert 'TIER_1' -> 1
    risk_str = str(row["risk"])
    risk_int = int(risk_str.split("_")[-1]) if "_" in risk_str else 1

    return {
        "id": row["id"],
        "title": row["title"],
        "state": str(row["state"]),
        "risk_tier": risk_int,
        "created_at": row["created_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def get_content(engine, tenant_id: str, content_id: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    title,
                    state::text AS state,
                    risk::text AS risk,
                    created_at,
                    updated_at
                FROM public.content_items
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND id = CAST(:content_id AS uuid)
                """
            ),
            {"tenant_id": tenant_id, "content_id": content_id},
        ).mappings().first()

    if not row:
        raise KeyError("content not found")

    risk_str = str(row["risk"])
    risk_int = int(risk_str.split("_")[-1]) if "_" in risk_str else 1

    return {
        "id": row["id"],
        "title": row["title"],
        "state": str(row["state"]),
        "risk_tier": risk_int,
        "created_at": row["created_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def transition_content(engine, tenant_id: str, content_id: str, to_state: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE public.content_items
                SET state = CAST(:to_state AS content_state)
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND id = CAST(:content_id AS uuid)
                RETURNING
                    id::text AS id,
                    title,
                    state::text AS state,
                    risk::text AS risk,
                    created_at,
                    updated_at
                """
            ),
            {"tenant_id": tenant_id, "content_id": content_id, "to_state": to_state},
        ).mappings().first()

    if not row:
        raise KeyError("content not found")

    risk_str = str(row["risk"])
    risk_int = int(risk_str.split("_")[-1]) if "_" in risk_str else 1

    return {
        "id": row["id"],
        "title": row["title"],
        "state": str(row["state"]),
        "risk_tier": risk_int,
        "created_at": row["created_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# ----------------------------
# events
# ----------------------------
def append_event(
    engine,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict,
) -> dict:
    created_at = _utcnow()
    payload_json = _jsonb(payload)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO public.events
                    (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
                VALUES
                    (CAST(:tenant_id AS uuid),
                     :entity_type,
                     CAST(:entity_id AS uuid),
                     :event_type,
                     :actor_type,
                     :actor_id,
                     CAST(:payload AS jsonb),
                     :created_at)
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
        ).mappings().first()

    if not row:
        raise RuntimeError("Failed to append event")

    return {
        "id": row["id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "event_type": row["event_type"],
        "actor_type": row["actor_type"],
        "actor_id": row["actor_id"],
        "payload": row["payload"],
        "created_at": row["created_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def list_events(engine, tenant_id: str, entity_type: str, entity_id: str) -> list[dict]:
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
                FROM public.events
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND entity_type = :entity_type
                  AND entity_id = CAST(:entity_id AS uuid)
                ORDER BY created_at ASC
                """
            ),
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
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
                "payload": r["payload"],
                "created_at": r["created_at"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
    return out
