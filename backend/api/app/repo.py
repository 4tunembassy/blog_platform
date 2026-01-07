# backend/api/app/repo.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_core_tables_exist(engine: Engine) -> None:
    """
    Idempotent bootstrap for tables this API assumes exist.
    Does NOT try to manage enums/migrations; alembic handles that.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS public.events (
      id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      entity_type text NOT NULL,
      entity_id uuid NOT NULL,
      event_type text NOT NULL,
      actor_type text NOT NULL,
      actor_id text NULL,
      payload jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_events_tenant_entity_time
    ON public.events (tenant_id, entity_type, entity_id, created_at DESC);
    """
    with engine.begin() as conn:
        for stmt in ddl.split(";"):
            s = stmt.strip()
            if s:
                conn.exec_driver_sql(s)


def _risk_enum_value_from_int(risk_tier: int) -> str:
    # Only map what EXISTS in DB enum.
    # If DB only has TIER_1..TIER_3, never emit TIER_4.
    if risk_tier <= 1:
        return "TIER_1"
    if risk_tier == 2:
        return "TIER_2"
    # risk_tier >= 3 -> clamp to TIER_3
    return "TIER_3"


def _risk_int_from_enum(risk: str) -> int:
    return {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3}.get(risk, 1)


def create_content_item(
    engine: Engine,
    tenant_id: str,
    title: str,
    risk_tier: int,
    now: datetime,
    tenant_slug: str,
) -> Dict[str, Any]:
    risk_enum = _risk_enum_value_from_int(risk_tier)

    sql = text(
        """
        INSERT INTO public.content_items (tenant_id, title, risk, state, created_at, updated_at)
        VALUES (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier), 'INGESTED', :now, :now)
        RETURNING
            id::text AS id,
            title,
            state::text AS state,
            risk::text AS risk,
            created_at,
            updated_at
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": tenant_id, "title": title, "risk": risk_enum, "now": now},
        ).mappings().one()

        # Write an event (payload must be json string, not dict object for psycopg)
        payload = {
            "title": title,
            "risk_tier": _risk_int_from_enum(row["risk"]),
            "state": row["state"],
            "tenant_slug": tenant_slug,
        }

        conn.execute(
            text(
                """
                INSERT INTO public.events
                  (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
                VALUES
                  (CAST(:tenant_id AS uuid), :entity_type, CAST(:entity_id AS uuid), :event_type,
                   :actor_type, :actor_id, CAST(:payload AS jsonb), :created_at)
                """
            ),
            {
                "tenant_id": tenant_id,
                "entity_type": "content",
                "entity_id": row["id"],
                "event_type": "content.created",
                "actor_type": "system",
                "actor_id": None,
                "payload": json.dumps(payload),
                "created_at": now,
            },
        )

    # Return ISO strings so response model is stable
    return {
        "id": row["id"],
        "title": row["title"],
        "state": row["state"],
        "risk_tier": _risk_int_from_enum(row["risk"]),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def get_allowed_transitions(engine: Engine, tenant_id: str, content_id: UUID) -> List[Dict[str, Any]]:
    # No DB query needed yet; policy is static for now.
    # Returning directly avoids SQL binding/casting issues.
    return [
        {
            "content_id": str(content_id),
            "from_state": "INGESTED",
            "risk_tier": 1,
            "allowed": ["CLASSIFIED", "DEFERRED", "RETIRED"],
        }
    ]



def list_events_for_entity(engine: Engine, tenant_id: str, entity_type: str, entity_id: UUID) -> List[Dict[str, Any]]:
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
        FROM public.events
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND entity_type = :entity_type
          AND entity_id = CAST(:entity_id AS uuid)
        ORDER BY created_at ASC
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": str(entity_id)},
        ).mappings().all()

    # Make payload plain dict and created_at string (API friendly)
    out: List[Dict[str, Any]] = []
    for r in rows:
        payload = r["payload"]
        # psycopg may already decode jsonb into dict; keep as-is
        out.append(
            {
                "id": r["id"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "event_type": r["event_type"],
                "actor_type": r["actor_type"],
                "actor_id": r["actor_id"],
                "payload": payload,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return out
