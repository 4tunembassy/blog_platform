from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Engine

def _now():
    return datetime.now(timezone.utc)

def create_content(engine: Engine, title: str, risk_tier: int) -> dict:
    content_id = str(uuid.uuid4())
    now = _now()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO content_items (id, title, state, risk_tier, created_at, updated_at)
                VALUES (:id, :title, :state, :risk_tier, :created_at, :updated_at)
            """),
            {
                "id": content_id,
                "title": title,
                "state": "intake",
                "risk_tier": risk_tier,
                "created_at": now,
                "updated_at": now,
            },
        )
    return get_content(engine, content_id)

def get_content(engine: Engine, content_id: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT id, title, state, risk_tier, created_at, updated_at
                FROM content_items
                WHERE id = :id
            """),
            {"id": content_id},
        ).mappings().first()
        if not row:
            raise KeyError("Content not found")
        return dict(row)

def list_events(engine: Engine, entity_type: str, entity_id: str) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at
                FROM provenance_events
                WHERE entity_type = :entity_type AND entity_id = :entity_id
                ORDER BY created_at ASC
            """),
            {"entity_type": entity_type, "entity_id": entity_id},
        ).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"]) if isinstance(d["payload"], str) else d["payload"]
            out.append(d)
        return out

def append_event(engine: Engine, *, entity_type: str, entity_id: str, event_type: str, actor_type: str, actor_id: str | None, payload: dict) -> dict:
    event_id = str(uuid.uuid4())
    now = _now()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO provenance_events (id, entity_type, entity_id, event_type, actor_type, actor_id, payload, created_at)
                VALUES (:id, :entity_type, :entity_id, :event_type, :actor_type, :actor_id, :payload, :created_at)
            """),
            {
                "id": event_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "payload": json.dumps(payload),
                "created_at": now,
            },
        )
    return {
        "id": event_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "payload": payload,
        "created_at": now,
    }

def transition_content(engine: Engine, content_id: str, to_state: str) -> dict:
    now = _now()
    with engine.begin() as conn:
        res = conn.execute(
            text("""
                UPDATE content_items
                SET state = :to_state, updated_at = :updated_at
                WHERE id = :id
            """),
            {"id": content_id, "to_state": to_state, "updated_at": now},
        )
        if res.rowcount == 0:
            raise KeyError("Content not found")
    return get_content(engine, content_id)
