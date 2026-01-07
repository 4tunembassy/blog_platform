from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine


# ----------------------------
# Helpers (safe + deterministic)
# ----------------------------

def _sort_to_order_by(sort: str) -> str:
    """
    Allowed sort values (explicit allow-list to avoid SQL injection):
      - created_at_desc (default)
      - created_at_asc
      - updated_at_desc
      - updated_at_asc
      - title_asc
      - title_desc
    """
    s = (sort or "").strip().lower()
    if s == "created_at_asc":
        return "created_at ASC"
    if s == "updated_at_desc":
        return "updated_at DESC"
    if s == "updated_at_asc":
        return "updated_at ASC"
    if s == "title_asc":
        return "title ASC"
    if s == "title_desc":
        return "title DESC"
    return "created_at DESC"


def _risk_enum_to_int_sql(expr: str = "risk") -> str:
    """
    IMPORTANT:
    risk is a Postgres ENUM in this project.

    If you write:
        WHEN risk = 'TIER_4' THEN 4
    Postgres may attempt to coerce 'TIER_4' into the enum type, and if that
    label isn't present in the enum, it crashes even if no row has TIER_4.

    So we ALWAYS compare expr::text (string) to avoid enum label errors.
    """
    return f"""(
        CASE
            WHEN ({expr})::text = 'TIER_1' THEN 1
            WHEN ({expr})::text = 'TIER_2' THEN 2
            WHEN ({expr})::text = 'TIER_3' THEN 3
            WHEN ({expr})::text = 'TIER_4' THEN 4
            ELSE 1
        END
    )"""


def _risk_int_to_label(risk_tier: int) -> str:
    """
    MVP enforcement (Tier 1 & Tier 2 only).
    If later you enable Tier 3/4, widen this mapping + update enum/migrations.
    """
    if risk_tier == 1:
        return "TIER_1"
    if risk_tier == 2:
        return "TIER_2"
    raise ValueError("risk_tier must be 1 or 2 for MVP")


# ----------------------------
# CRUD / Queries
# ----------------------------

def create_content_item(engine: Engine, tenant_id: UUID, title: str, risk_tier: int) -> Dict[str, Any]:
    risk_label = _risk_int_to_label(int(risk_tier))

    sql = text(f"""
        INSERT INTO public.content_items
            (tenant_id, title, risk, state, created_at, updated_at)
        VALUES
            (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier), 'INGESTED', NOW(), NOW())
        RETURNING
            id::text AS id,
            title,
            state::text AS state,
            {_risk_enum_to_int_sql("risk")} AS risk_tier,
            created_at,
            updated_at;
    """)

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": str(tenant_id), "title": title, "risk": risk_label},
        ).mappings().one()

    return dict(row)


def get_content_by_id(engine: Engine, tenant_id: UUID, content_id: UUID) -> Dict[str, Any]:
    """
    main.py expects this symbol.
    """
    sql = text(f"""
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            {_risk_enum_to_int_sql("risk")} AS risk_tier,
            created_at,
            updated_at
        FROM public.content_items
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid);
    """)

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": str(tenant_id), "content_id": str(content_id)},
        ).mappings().one()

    return dict(row)


def list_content(
    engine: Engine,
    tenant_id: UUID,
    limit: int = 20,
    offset: int = 0,
    sort: str = "created_at_desc",
    q: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    order_by = _sort_to_order_by(sort)

    where_parts = ["tenant_id = CAST(:tenant_id AS uuid)"]
    params: Dict[str, Any] = {"tenant_id": str(tenant_id), "limit": int(limit), "offset": int(offset)}

    if q:
        where_parts.append("title ILIKE :q")
        params["q"] = f"%{q}%"

    where_sql = " AND ".join(where_parts)

    sql_items = text(f"""
        SELECT
            id::text AS id,
            title,
            state::text AS state,
            {_risk_enum_to_int_sql("risk")} AS risk_tier,
            created_at,
            updated_at
        FROM public.content_items
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset;
    """)

    sql_total = text(f"""
        SELECT COUNT(*)::int AS total
        FROM public.content_items
        WHERE {where_sql};
    """)

    with engine.begin() as conn:
        rows = conn.execute(sql_items, params).mappings().all()
        total = conn.execute(sql_total, params).mappings().one()["total"]

    return [dict(r) for r in rows], int(total)


def list_content_events(engine: Engine, tenant_id: UUID, content_id: UUID) -> List[Dict[str, Any]]:
    sql = text("""
        SELECT
            id::text AS id,
            entity_type,
            entity_id::text AS entity_id,
            event_type,
            actor_type,
            COALESCE(actor_id::text, '') AS actor_id,
            payload,
            created_at
        FROM public.events
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND entity_type = 'content'
          AND entity_id = CAST(:content_id AS uuid)
        ORDER BY created_at ASC;
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {"tenant_id": str(tenant_id), "content_id": str(content_id)},
        ).mappings().all()

    return [dict(r) for r in rows]


# ----------------------------
# Governance: allowed + transition
# ----------------------------

def get_allowed_transitions(engine: Engine, tenant_id: UUID, content_id: UUID) -> Dict[str, Any]:
    """
    MVP transitions:
      INGESTED   -> CLASSIFIED, DEFERRED, RETIRED
      CLASSIFIED -> RETIRED
      DEFERRED   -> INGESTED, RETIRED
      RETIRED    -> (none)
    """
    sql = text(f"""
        WITH c AS (
            SELECT
                id::text AS content_id,
                state::text AS state,
                {_risk_enum_to_int_sql("risk")} AS risk_tier
            FROM public.content_items
            WHERE tenant_id = CAST(:tenant_id AS uuid)
              AND id = CAST(:content_id AS uuid)
        )
        SELECT
            c.content_id,
            c.state AS from_state,
            c.risk_tier,
            CASE
                WHEN c.state = 'INGESTED'   THEN ARRAY['CLASSIFIED','DEFERRED','RETIRED']::text[]
                WHEN c.state = 'CLASSIFIED' THEN ARRAY['RETIRED']::text[]
                WHEN c.state = 'DEFERRED'   THEN ARRAY['INGESTED','RETIRED']::text[]
                ELSE ARRAY[]::text[]
            END AS allowed
        FROM c;
    """)

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"tenant_id": str(tenant_id), "content_id": str(content_id)},
        ).mappings().one()

    return dict(row)


def transition_content(engine: Engine, tenant_id: UUID, content_id: UUID, to_state: str) -> Dict[str, Any]:
    """
    Update state + write event. (Assumes main.py enforces allowed transitions.)
    """
    to_state = (to_state or "").strip().upper()

    sql_get = text(f"""
        SELECT
            id::text AS content_id,
            state::text AS from_state,
            {_risk_enum_to_int_sql("risk")} AS risk_tier
        FROM public.content_items
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid);
    """)

    sql_update = text("""
        UPDATE public.content_items
        SET state = CAST(:to_state AS content_state),
            updated_at = NOW()
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND id = CAST(:content_id AS uuid)
        RETURNING id::text AS content_id;
    """)

    sql_event = text("""
        INSERT INTO public.events
            (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
        VALUES
            (CAST(:tenant_id AS uuid), 'content', CAST(:content_id AS uuid), 'content.transitioned',
             'system', NULL, :payload::jsonb, NOW());
    """)

    with engine.begin() as conn:
        cur = conn.execute(
            sql_get, {"tenant_id": str(tenant_id), "content_id": str(content_id)}
        ).mappings().one()

        conn.execute(
            sql_update,
            {"tenant_id": str(tenant_id), "content_id": str(content_id), "to_state": to_state},
        )

        payload = {
            "from_state": cur["from_state"],
            "to_state": to_state,
            "risk_tier": int(cur["risk_tier"]),
        }

        conn.execute(
            sql_event,
            {
                "tenant_id": str(tenant_id),
                "content_id": str(content_id),
                "payload": json.dumps(payload),
            },
        )

    return {
        "content_id": str(content_id),
        "from_state": cur["from_state"],
        "to_state": to_state,
        "risk_tier": int(cur["risk_tier"]),
    }
