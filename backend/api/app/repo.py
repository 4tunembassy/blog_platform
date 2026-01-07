import json
from uuid import UUID
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------- helpers ----------

def _risk_enum_from_tier(risk_tier: int) -> str:
    """
    DB enum risk_tier supports: TIER_1, TIER_2, TIER_3
    Clamp and keep safe.
    """
    if risk_tier <= 1:
        return "TIER_1"
    if risk_tier == 2:
        return "TIER_2"
    return "TIER_3"


def _risk_tier_from_enum(risk_enum: str) -> int:
    return {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3}.get(risk_enum, 1)


# ---------- content ----------

def create_content_item(engine: Engine, tenant_id: str, title: str, risk_tier: int) -> Dict[str, Any]:
    risk_enum = _risk_enum_from_tier(risk_tier)

    sql = text("""
        INSERT INTO public.content_items (tenant_id, title, risk, state, created_at, updated_at)
        VALUES (
            CAST(:tenant_id AS uuid),
            :title,
            CAST(:risk AS risk_tier),
            CAST('INGESTED' AS content_state),
            now(),
            now()
        )
        RETURNING
            id::text AS id,
            title,
            state::text AS state,
            risk::text AS risk_enum,
            created_at,
            updated_at
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"tenant_id": tenant_id, "title": title, "risk": risk_enum}).mappings().one()
        out = dict(row)
        out["risk_tier"] = _risk_tier_from_enum(out.pop("risk_enum"))
        return out


def get_content_by_id(conn, tenant_id: str, content_id: UUID) -> Optional[Dict[str, Any]]:
    sql = text("""
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            risk::text AS risk_enum,
            created_at,
            updated_at
        FROM public.content_items
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        LIMIT 1
    """)
    row = conn.execute(sql, {"tenant_id": tenant_id, "content_id": str(content_id)}).mappings().first()
    if not row:
        return None
    out = dict(row)
    out["risk_tier"] = _risk_tier_from_enum(out.pop("risk_enum"))
    return out


def get_content(engine: Engine, tenant_id: str, content_id: UUID) -> Optional[Dict[str, Any]]:
    with engine.begin() as conn:
        return get_content_by_id(conn, tenant_id, content_id)


def list_content(
    engine: Engine,
    tenant_id: str,
    limit: int = 20,
    offset: int = 0,
    state: Optional[str] = None,
    risk_tier: Optional[int] = None,
    q: Optional[str] = None,
    sort: str = "created_at_desc",
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List content items with filters + pagination.
    - state: INGESTED/CLASSIFIED/DEFERRED/RETIRED
    - risk_tier: 1..3
    - q: title search (ILIKE)
    - sort: created_at_desc | created_at_asc | updated_at_desc | updated_at_asc
    """
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    where = ["tenant_id = CAST(:tenant_id AS uuid)"]
    params: Dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if state:
        where.append("state = CAST(:state AS content_state)")
        params["state"] = state

    if risk_tier is not None:
        params["risk_enum"] = _risk_enum_from_tier(int(risk_tier))
        where.append("risk = CAST(:risk_enum AS risk_tier)")

    if q and q.strip():
        where.append("title ILIKE :q")
        params["q"] = f"%{q.strip()}%"

    order_by = {
        "created_at_desc": "created_at DESC",
        "created_at_asc": "created_at ASC",
        "updated_at_desc": "updated_at DESC",
        "updated_at_asc": "updated_at ASC",
    }.get(sort, "created_at DESC")

    where_sql = " AND ".join(where)

    count_sql = text(f"""
        SELECT COUNT(*)::int AS total
        FROM public.content_items
        WHERE {where_sql}
    """)

    list_sql = text(f"""
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            risk::text AS risk_enum,
            created_at,
            updated_at
        FROM public.content_items
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT :limit
        OFFSET :offset
    """)

    with engine.begin() as conn:
        total = conn.execute(count_sql, params).scalar_one()
        rows = conn.execute(list_sql, params).mappings().all()

    items: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["risk_tier"] = _risk_tier_from_enum(d.pop("risk_enum"))
        items.append(d)

    return items, int(total)


def update_content_state(conn, tenant_id: str, content_id: UUID, to_state: str) -> Dict[str, Any]:
    sql = text("""
        UPDATE public.content_items
        SET state = CAST(:to_state AS content_state),
            updated_at = now()
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        RETURNING
            id::text AS id,
            title,
            state::text AS state,
            risk::text AS risk_enum,
            created_at,
            updated_at
    """)
    row = conn.execute(
        sql,
        {"tenant_id": tenant_id, "content_id": str(content_id), "to_state": to_state},
    ).mappings().one()

    out = dict(row)
    out["risk_tier"] = _risk_tier_from_enum(out.pop("risk_enum"))
    return out


# ---------- events ----------

def insert_event(conn, tenant_id: str, entity_type: str, entity_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    sql = text("""
        INSERT INTO public.events (
            tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload
        )
        VALUES (
            CAST(:tenant_id AS uuid),
            :entity_type,
            CAST(:entity_id AS uuid),
            :event_type,
            'system',
            NULL,
            CAST(:payload AS jsonb)
        )
    """)
    conn.execute(sql, {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": event_type,
        "payload": json.dumps(payload),
    })


def list_events(engine: Engine, tenant_id: str, entity_type: str, entity_id: UUID) -> List[Dict[str, Any]]:
    sql = text("""
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
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": str(entity_id)}).mappings().all()
    return [dict(r) for r in rows]


# ---------- workflow policy ----------

def compute_allowed(from_state: str, risk_tier: int) -> List[str]:
    # Policy v0 (simple + deterministic):
    if from_state == "INGESTED":
        return ["CLASSIFIED", "DEFERRED", "RETIRED"]
    if from_state == "DEFERRED":
        return ["CLASSIFIED", "RETIRED"]
    if from_state == "CLASSIFIED":
        return ["RETIRED"]
    return []


def get_allowed_transitions(engine: Engine, tenant_id: str, content_id: UUID) -> Optional[Dict[str, Any]]:
    with engine.begin() as conn:
        item = get_content_by_id(conn, tenant_id, content_id)
        if not item:
            return None

        from_state = item["state"]
        risk_tier = int(item["risk_tier"])
        allowed = compute_allowed(from_state, risk_tier)

        return {
            "content_id": str(content_id),
            "from_state": from_state,
            "risk_tier": risk_tier,
            "allowed": allowed,
        }
