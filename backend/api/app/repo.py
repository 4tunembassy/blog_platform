from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


# -----------------------------
# Helpers
# -----------------------------
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _risk_enum(risk_tier: int) -> str:
    # DB enum is risk_tier: TIER_1, TIER_2, TIER_3...
    # API sends 1,2,3
    if risk_tier < 1:
        risk_tier = 1
    return f"TIER_{int(risk_tier)}"


def _jsonb(value: Any) -> str:
    # Always store JSON as a string parameter and CAST(:x AS jsonb) in SQL
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# -----------------------------
# Content CRUD
# -----------------------------
def create_content(engine, tenant_id: str, title: str, risk_tier: int) -> dict:
    risk = _risk_enum(risk_tier)
    now = _now_utc()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO public.content_items
                    (tenant_id, title, risk, state, created_at, updated_at)
                VALUES
                    (CAST(:tenant_id AS uuid), :title, CAST(:risk AS risk_tier), 'INGESTED'::content_state, :now, :now)
                RETURNING
                    id::text AS id,
                    title,
                    state::text AS state,
                    risk::text AS risk,
                    created_at,
                    updated_at
                """
            ),
            {"tenant_id": tenant_id, "title": title, "risk": risk, "now": now},
        ).mappings().first()

    if not row:
        raise RuntimeError("Failed to create content")

    # Normalize output risk_tier back to int if possible
    out = dict(row)
    out["risk_tier"] = int(out["risk"].split("_")[1]) if out.get("risk") else risk_tier
    out.pop("risk", None)
    return out


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

    out = dict(row)
    out["risk_tier"] = int(out["risk"].split("_")[1]) if out.get("risk") else 1
    out.pop("risk", None)
    return out


def transition_content(engine, tenant_id: str, content_id: str, to_state: str) -> dict:
    # content_state enum values are like INGESTED, CLASSIFIED, DEFERRED, RETIRED, etc.
    now = _now_utc()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE public.content_items
                SET state = CAST(:to_state AS content_state),
                    updated_at = :now
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
            {
                "tenant_id": tenant_id,
                "content_id": content_id,
                "to_state": to_state,
                "now": now,
            },
        ).mappings().first()

    if not row:
        raise KeyError("content not found")

    out = dict(row)
    out["risk_tier"] = int(out["risk"].split("_")[1]) if out.get("risk") else 1
    out.pop("risk", None)
    return out


# -----------------------------
# Events table (public.events)
# -----------------------------
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
    now = _now_utc()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO public.events
                    (tenant_id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
                VALUES
                    (CAST(:tenant_id AS uuid), :entity_type, CAST(:entity_id AS uuid),
                     :event_type, :actor_type, :actor_id,
                     CAST(:payload AS jsonb), :created_at)
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
                "payload": _jsonb(payload),
                "created_at": now,
            },
        ).mappings().first()

    return dict(row) if row else {}


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

    return [dict(r) for r in rows]


# -----------------------------
# Provenance table (public.provenance_events)
# -----------------------------
def append_provenance_event(
    engine,
    tenant_id: str,
    content_id: str | None,
    intake_id: str | None,
    agent_name: str,
    status: str,
    details: dict,
    model_name: str | None = None,
    prompt_version_id: str | None = None,
    policy_version_id: str | None = None,
    input_hash: str | None = None,
    output_hash: str | None = None,
) -> dict:
    """
    Lasting fix:
    - DO NOT use CASE WHEN for NULL UUID params.
    - CAST(NULL AS uuid) is NULL; Postgres will accept it cleanly.
    """
    now = _now_utc()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO public.provenance_events
                    (tenant_id, content_id, intake_id, agent_name,
                     prompt_version_id, policy_version_id, model_name,
                     input_hash, output_hash, status, details, created_at)
                VALUES
                    (CAST(:tenant_id AS uuid),
                     CAST(:content_id AS uuid),
                     CAST(:intake_id AS uuid),
                     :agent_name,
                     CAST(:prompt_version_id AS uuid),
                     CAST(:policy_version_id AS uuid),
                     :model_name,
                     :input_hash,
                     :output_hash,
                     :status,
                     CAST(:details AS jsonb),
                     :created_at)
                RETURNING
                    id::text AS id,
                    tenant_id::text AS tenant_id,
                    content_id::text AS content_id,
                    intake_id::text AS intake_id,
                    agent_name,
                    prompt_version_id::text AS prompt_version_id,
                    policy_version_id::text AS policy_version_id,
                    model_name,
                    input_hash,
                    output_hash,
                    status,
                    details,
                    created_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "content_id": content_id,
                "intake_id": intake_id,
                "agent_name": agent_name,
                "prompt_version_id": prompt_version_id,
                "policy_version_id": policy_version_id,
                "model_name": model_name,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "status": status,
                "details": _jsonb(details),
                "created_at": now,
            },
        ).mappings().first()

    return dict(row) if row else {}


def list_provenance_events(engine, tenant_id: str, content_id: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    tenant_id::text AS tenant_id,
                    content_id::text AS content_id,
                    intake_id::text AS intake_id,
                    agent_name,
                    prompt_version_id::text AS prompt_version_id,
                    policy_version_id::text AS policy_version_id,
                    model_name,
                    input_hash,
                    output_hash,
                    status,
                    details,
                    created_at
                FROM public.provenance_events
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND content_id = CAST(:content_id AS uuid)
                ORDER BY created_at ASC
                """
            ),
            {"tenant_id": tenant_id, "content_id": content_id},
        ).mappings().all()

    return [dict(r) for r in rows]
