from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine


# -----------------------------
# Helpers
# -----------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Any) -> str:
    # dt may be datetime (psycopg) or already string
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.isoformat().replace("+00:00", "Z")
    return str(dt)


def _risk_enum(risk_tier: int) -> str:
    # DB enum values are expected like: TIER_1, TIER_2, ...
    rt = int(risk_tier)
    if rt < 1 or rt > 4:
        rt = 1
    return f"TIER_{rt}"


# -----------------------------
# Content
# -----------------------------

def create_content_item(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> Dict[str, Any]:
    now = _utc_now()
    risk = _risk_enum(risk_tier)

    sql = text(
        """
        INSERT INTO public.content_items (tenant_id, title, risk, state, created_at, updated_at)
        VALUES (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier), 'INGESTED', :now, :now)
        RETURNING
            id::text AS id,
            title,
            state::text AS state,
            (CASE
                WHEN risk='TIER_1' THEN 1
                WHEN risk='TIER_2' THEN 2
                WHEN risk='TIER_3' THEN 3
                WHEN risk='TIER_4' THEN 4
                ELSE 1
             END) AS risk_tier,
            created_at,
            updated_at
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": tenant_id, "title": title, "risk": risk, "now": now},
        ).mappings().one()

    return {
        "id": row["id"],
        "title": row["title"],
        "state": row["state"],
        "risk_tier": int(row["risk_tier"]),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
    }


def get_content_by_id(engine: Engine, tenant_id: str, content_id: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            (CASE
                WHEN risk='TIER_1' THEN 1
                WHEN risk='TIER_2' THEN 2
                WHEN risk='TIER_3' THEN 3
                WHEN risk='TIER_4' THEN 4
                ELSE 1
             END) AS risk_tier,
            created_at,
            updated_at
        FROM public.content_items
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql, {"tenant_id": tenant_id, "content_id": content_id}
        ).mappings().one_or_none()

    if not row:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "state": row["state"],
        "risk_tier": int(row["risk_tier"]),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
    }


def list_content(
    engine: Engine,
    tenant_id: str,
    limit: int,
    offset: int,
    sort: str,
    q: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns (items, total)
    """
    sort = (sort or "created_at_desc").strip()
    order_by = "created_at DESC" if sort == "created_at_desc" else "created_at ASC"

    base_where = "tenant_id = CAST(:tenant_id AS uuid)"
    params: Dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if q and q.strip():
        base_where += " AND title ILIKE :q"
        params["q"] = f"%{q.strip()}%"

    sql_items = text(
        f"""
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            (CASE
                WHEN risk='TIER_1' THEN 1
                WHEN risk='TIER_2' THEN 2
                WHEN risk='TIER_3' THEN 3
                WHEN risk='TIER_4' THEN 4
                ELSE 1
             END) AS risk_tier,
            created_at,
            updated_at
        FROM public.content_items
        WHERE {base_where}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
        """
    )

    sql_total = text(
        f"""
        SELECT COUNT(*)::int AS total
        FROM public.content_items
        WHERE {base_where}
        """
    )

    with engine.begin() as conn:
        total_row = conn.execute(sql_total, params).mappings().one()
        rows = conn.execute(sql_items, params).mappings().all()

    items = [
        {
            "id": r["id"],
            "title": r["title"],
            "state": r["state"],
            "risk_tier": int(r["risk_tier"]),
            "created_at": _iso(r["created_at"]),
            "updated_at": _iso(r["updated_at"]),
        }
        for r in rows
    ]
    return items, int(total_row["total"])


# -----------------------------
# Allowed transitions
# (placeholder logic — currently hardcoded by state + tier)
# -----------------------------

def get_allowed_transitions(engine: Engine, tenant_id: str, content_id: str) -> Dict[str, Any]:
    """
    Minimal governance rules for now:
      - INGESTED -> CLASSIFIED, DEFERRED, RETIRED
      - CLASSIFIED -> RETIRED
      - DEFERRED -> INGESTED, RETIRED
      - RETIRED -> (none)
    Risk tier is returned for context.
    """
    item = get_content_by_id(engine, tenant_id, content_id)
    if not item:
        raise ValueError("Content not found")

    state = item["state"]
    risk_tier = int(item["risk_tier"])

    if state == "INGESTED":
        allowed = ["CLASSIFIED", "DEFERRED", "RETIRED"]
    elif state == "CLASSIFIED":
        allowed = ["RETIRED"]
    elif state == "DEFERRED":
        allowed = ["INGESTED", "RETIRED"]
    else:
        allowed = []

    return {
        "content_id": content_id,
        "from_state": state,
        "risk_tier": risk_tier,
        "allowed": allowed,
    }


def transition_content(engine: Engine, tenant_id: str, content_id: str, to_state: str) -> Dict[str, Any]:
    allowed_info = get_allowed_transitions(engine, tenant_id, content_id)
    from_state = allowed_info["from_state"]
    risk_tier = allowed_info["risk_tier"]

    to_state_norm = (to_state or "").strip().upper()
    if to_state_norm not in allowed_info["allowed"]:
        raise ValueError(f"Transition not allowed: {from_state} -> {to_state_norm}")

    now = _utc_now()

    sql = text(
        """
        UPDATE public.content_items
        SET state = CAST(:to_state AS content_state),
            updated_at = :now
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        RETURNING id::text AS id
        """
    )

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "tenant_id": tenant_id,
                "content_id": content_id,
                "to_state": to_state_norm,
                "now": now,
            },
        ).mappings().one_or_none()

    if not row:
        raise ValueError("Content not found")

    return {
        "content_id": content_id,
        "from_state": from_state,
        "to_state": to_state_norm,
        "risk_tier": risk_tier,
    }


# -----------------------------
# Events
# -----------------------------

def insert_event(
    engine: Engine,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: Dict[str, Any],
    actor_type: str = "system",
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = _utc_now()

    sql = text(
        """
        INSERT INTO public.events
            (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
        VALUES
            (CAST(:tenant_id AS uuid), :entity_type, CAST(:entity_id AS uuid), :event_type,
             :actor_type, :actor_id, CAST(:payload AS jsonb), :now)
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
                "payload": payload and __import__("json").dumps(payload) or "{}",
                "now": now,
            },
        ).mappings().one()

    return {
        "id": row["id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "event_type": row["event_type"],
        "actor_type": row["actor_type"],
        "actor_id": row["actor_id"],
        "payload": row["payload"],
        "created_at": _iso(row["created_at"]),
    }


def list_events(engine: Engine, tenant_id: str, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
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
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
        ).mappings().all()

    return [
        {
            "id": r["id"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "event_type": r["event_type"],
            "actor_type": r["actor_type"],
            "actor_id": r["actor_id"],
            "payload": r["payload"],
            "created_at": _iso(r["created_at"]),
        }
        for r in rows
    ]
