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
        return conn.execute(
            text("SELECT id::text FROM tenants WHERE slug=:slug"),
            {"slug": tenant_slug},
        ).scalar_one_or_none()

def _table_columns(engine: Engine, table: str, schema: str = "public") -> list[str]:
    with engine.begin() as conn:
        return list(
            conn.execute(
                text(
                    '''
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema=:schema AND table_name=:table
                    ORDER BY ordinal_position
                    '''
                ),
                {"schema": schema, "table": table},
            ).scalars().all()
        )

def _first_nonempty(*vals: Any) -> Any:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None

def create_content(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> Mapping[str, Any]:
    cols = set(_table_columns(engine, "content_items"))
    now = datetime.now(timezone.utc)

    insert_cols = ["tenant_id"]
    values_sql = ["CAST(:tenant_id AS uuid)"]
    params: dict[str, Any] = {"tenant_id": tenant_id}

    if "title" in cols:
        insert_cols.append("title")
        values_sql.append(":title")
        params["title"] = title

    if "risk_tier" in cols:
        insert_cols.append("risk_tier")
        values_sql.append(":risk_tier")
        params["risk_tier"] = int(risk_tier)
        risk_return = "risk_tier::text AS risk_any"
    else:
        if "risk" in cols:
            insert_cols.append("risk")
            values_sql.append("CAST(:risk AS risk_tier)")
            params["risk"] = risk_int_to_enum(risk_tier)
        risk_return = "risk::text AS risk_any"

    sql = f'''
        INSERT INTO content_items ({", ".join(insert_cols)})
        VALUES ({", ".join(values_sql)})
        RETURNING
          id::text AS id,
          state::text AS state,
          {risk_return},
          created_at,
          updated_at
    '''

    with engine.begin() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    risk_any = row.get("risk_any")
    if "risk_tier" in cols:
        try:
            risk_out = int(risk_any)
        except Exception:
            risk_out = int(risk_tier) if risk_tier else 1
    else:
        risk_out = risk_enum_to_int(risk_any)

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_out,
        "created_at": row.get("created_at") or now,
        "updated_at": row.get("updated_at") or now,
    }

def get_content(engine: Engine, tenant_id: str, content_id: str) -> Mapping[str, Any]:
    cols = set(_table_columns(engine, "content_items"))
    risk_col = "risk_tier" if "risk_tier" in cols else "risk"
    title_col = "title" if "title" in cols else None

    select_title = (f", {title_col} AS title" if title_col else "")
    with engine.begin() as conn:
        row = conn.execute(
            text(
                f'''
                SELECT
                  id::text AS id,
                  state::text AS state,
                  {risk_col}::text AS risk_any
                  {select_title},
                  created_at,
                  updated_at
                FROM content_items
                WHERE id = CAST(:id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
                '''
            ),
            {"id": content_id, "tenant_id": tenant_id},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")

    if title_col:
        title = row.get("title") or "(no title)"
    else:
        title = _get_title_from_provenance(engine, tenant_id=tenant_id, content_id=content_id) or "(no title stored yet)"

    if risk_col == "risk_tier":
        try:
            risk_out = int(row.get("risk_any"))
        except Exception:
            risk_out = 1
    else:
        risk_out = risk_enum_to_int(row.get("risk_any") or "TIER_1")

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_out,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def transition_content(engine: Engine, tenant_id: str, content_id: str, to_state: str) -> Mapping[str, Any]:
    cols = set(_table_columns(engine, "content_items"))
    risk_col = "risk_tier" if "risk_tier" in cols else "risk"
    title_col = "title" if "title" in cols else None

    returning_title = ", title AS title" if title_col else ""

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f'''
                UPDATE content_items
                SET state = CAST(:to_state AS content_state)
                WHERE id = CAST(:id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
                RETURNING
                  id::text AS id,
                  state::text AS state,
                  {risk_col}::text AS risk_any,
                  created_at,
                  updated_at
                  {returning_title}
                '''
            ),
            {"to_state": to_state, "id": content_id, "tenant_id": tenant_id},
        ).mappings().first()

    if not row:
        raise KeyError("Not found")

    if title_col:
        title = row.get("title") or "(no title)"
    else:
        title = _get_title_from_provenance(engine, tenant_id=tenant_id, content_id=content_id) or "(no title stored yet)"

    if risk_col == "risk_tier":
        try:
            risk_out = int(row.get("risk_any"))
        except Exception:
            risk_out = 1
    else:
        risk_out = risk_enum_to_int(row.get("risk_any") or "TIER_1")

    return {
        "id": row["id"],
        "title": title,
        "state": row["state"],
        "risk_tier": risk_out,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def append_event(
    engine: Engine,
    *,
    tenant_id: str,
    content_id: str | None,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    details: dict[str, Any],
    status: str = "ok",
) -> None:
    cols = set(_table_columns(engine, "provenance_events"))

    agent_name_val = _first_nonempty(actor_id, actor_type, "system")
    now = datetime.now(timezone.utc)

    full_details: dict[str, Any] = {
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        **(details or {}),
    }

    data: dict[str, Any] = {}

    if "tenant_id" in cols:
        data["tenant_id"] = tenant_id
    if content_id and "content_id" in cols:
        data["content_id"] = content_id

    if "agent_name" in cols:
        data["agent_name"] = agent_name_val
    if "status" in cols:
        data["status"] = status
    if "details" in cols:
        data["details"] = json.dumps(full_details)
    if "created_at" in cols:
        data["created_at"] = now

    col_list = ", ".join(data.keys())
    bind_list = ", ".join(f":{k}" for k in data.keys())

    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO provenance_events ({col_list}) VALUES ({bind_list})"), data)

def list_events(engine: Engine, *, tenant_id: str, content_id: str) -> list[Mapping[str, Any]]:
    cols = set(_table_columns(engine, "provenance_events"))
    if "tenant_id" not in cols or "content_id" not in cols:
        return []

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                '''
                SELECT
                  id::text AS id,
                  details AS details,
                  created_at AS created_at
                FROM provenance_events
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND content_id = CAST(:content_id AS uuid)
                ORDER BY created_at DESC
                LIMIT 200
                '''
            ),
            {"tenant_id": tenant_id, "content_id": content_id},
        ).mappings().all()

    out = []
    for r in rows:
        det = r.get("details") or {}
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except Exception:
                det = {}
        out.append(
            {
                "id": r.get("id") or "",
                "entity_type": det.get("entity_type") or "content",
                "entity_id": det.get("entity_id") or content_id,
                "event_type": det.get("event_type") or "provenance",
                "actor_type": det.get("actor_type") or "system",
                "actor_id": det.get("actor_id"),
                "payload": det.get("payload") or det,
                "created_at": r.get("created_at"),
            }
        )
    return out

def _get_title_from_provenance(engine: Engine, *, tenant_id: str, content_id: str) -> str | None:
    for ev in list_events(engine, tenant_id=tenant_id, content_id=content_id):
        if ev.get("event_type") == "content.created":
            title = (ev.get("payload") or {}).get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
    return None
