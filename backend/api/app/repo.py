from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.engine import Engine

def risk_int_to_enum(risk_tier: int) -> str:
    if risk_tier not in (1, 2, 3):
        risk_tier = 1
    return f"TIER_{risk_tier}"

def risk_enum_to_int(risk_enum: str) -> int:
    try:
        return int(str(risk_enum).split("_")[-1])
    except Exception:
        return 1

def resolve_tenant_id(engine: Engine, tenant_slug: str) -> str | None:
    with engine.begin() as conn:
        tid = conn.execute(
            text("SELECT id::text FROM tenants WHERE slug=:slug"),
            {"slug": tenant_slug},
        ).scalar_one_or_none()
    return tid

def _table_columns(engine: Engine, table: str, schema: str = "public") -> list[str]:
    with engine.begin() as conn:
        cols = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=:schema AND table_name=:table
                ORDER BY ordinal_position
                """
            ),
            {"schema": schema, "table": table},
        ).scalars().all()
    return list(cols)

def create_content(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> Mapping[str, Any]:
    risk_enum = risk_int_to_enum(risk_tier)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO content_items (tenant_id, risk)
                VALUES (:tenant_id::uuid, :risk::risk_tier)
                RETURNING
                  id::text AS id,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                """
            ),
            {"tenant_id": tenant_id, "risk": risk_enum},
        ).mappings().first()

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_enum_to_int(row["risk"]),
        "created_at": row.get("created_at") or now,
        "updated_at": row.get("updated_at") or now,
    }

def get_content(engine: Engine, tenant_id: str, content_id: str) -> Mapping[str, Any]:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  id::text AS id,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                FROM content_items
                WHERE id = :id::uuid AND tenant_id = :tenant_id::uuid
                """
            ),
            {"id": content_id, "tenant_id": tenant_id},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")

    title = _get_title_from_events(engine, content_id) or "(no title stored yet)"

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_enum_to_int(row["risk"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def transition_content(engine: Engine, tenant_id: str, content_id: str, to_state: str) -> Mapping[str, Any]:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE content_items
                SET state = :to_state::content_state
                WHERE id = :id::uuid AND tenant_id = :tenant_id::uuid
                RETURNING
                  id::text AS id,
                  state::text AS state,
                  risk::text AS risk,
                  created_at,
                  updated_at
                """
            ),
            {"to_state": to_state, "id": content_id, "tenant_id": tenant_id},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")

    title = _get_title_from_events(engine, content_id) or "(no title stored yet)"

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_enum_to_int(row["risk"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

# ------------------------
# Events: provenance_events (dynamic)
# ------------------------
def append_event(
    engine: Engine,
    *,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict[str, Any],
    content_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    cols = _table_columns(engine, "provenance_events")
    data: dict[str, Any] = {}

    if "entity_type" in cols:
        data["entity_type"] = entity_type
    if "entity_id" in cols:
        data["entity_id"] = entity_id
    if "event_type" in cols:
        data["event_type"] = event_type
    if "actor_type" in cols:
        data["actor_type"] = actor_type
    if "actor_id" in cols:
        data["actor_id"] = actor_id
    if "payload" in cols:
        data["payload"] = json.dumps(payload)
    if "created_at" in cols:
        data["created_at"] = datetime.now(timezone.utc)

    if content_id and "content_id" in cols:
        data["content_id"] = content_id
    if tenant_id and "tenant_id" in cols:
        data["tenant_id"] = tenant_id

    if not data:
        return

    col_list = ", ".join(data.keys())
    bind_list = ", ".join(f":{k}" for k in data.keys())

    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO provenance_events ({col_list}) VALUES ({bind_list})"), data)

def list_events(engine: Engine, entity_type: str, entity_id: str) -> list[Mapping[str, Any]]:
    cols = _table_columns(engine, "provenance_events")

    select_sql_parts = []
    params = {"entity_type": entity_type, "entity_id": entity_id}

    select_sql_parts.append("id::text AS id" if "id" in cols else "NULL::text AS id")
    select_sql_parts.append("entity_type::text AS entity_type" if "entity_type" in cols else ":entity_type AS entity_type")
    select_sql_parts.append("entity_id::text AS entity_id" if "entity_id" in cols else ":entity_id AS entity_id")
    select_sql_parts.append("event_type::text AS event_type" if "event_type" in cols else "NULL::text AS event_type")
    select_sql_parts.append("actor_type::text AS actor_type" if "actor_type" in cols else "NULL::text AS actor_type")
    select_sql_parts.append("actor_id::text AS actor_id" if "actor_id" in cols else "NULL::text AS actor_id")
    select_sql_parts.append("payload::jsonb AS payload" if "payload" in cols else "'{}'::jsonb AS payload")
    select_sql_parts.append("created_at AS created_at" if "created_at" in cols else "now() AS created_at")

    where_parts = []
    if "entity_type" in cols:
        where_parts.append("entity_type = :entity_type")
    if "entity_id" in cols:
        where_parts.append("entity_id::text = :entity_id")
    where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
    order_clause = "created_at DESC" if "created_at" in cols else "1 DESC"

    sql = f"SELECT {', '.join(select_sql_parts)} FROM provenance_events WHERE {where_clause} ORDER BY {order_clause} LIMIT 200"

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    out: list[Mapping[str, Any]] = []
    for r in rows:
        payload_val = r.get("payload") or {}
        if isinstance(payload_val, str):
            try:
                payload_val = json.loads(payload_val)
            except Exception:
                payload_val = {}
        out.append({**r, "payload": payload_val})
    return out

def _get_title_from_events(engine: Engine, content_id: str) -> str | None:
    events = list_events(engine, "content", content_id)
    for ev in events:
        if ev.get("event_type") == "content.created":
            payload = ev.get("payload") or {}
            title = payload.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
    return None
