from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.engine import Engine

@dataclass
class WorkflowError(Exception):
    message: str
    def __str__(self) -> str:
        return self.message

def list_allowed_states(engine: Engine) -> set[str]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT unnest(enum_range(NULL::content_state))::text AS s")
        ).scalars().all()
    return set(rows)

def validate_transition(engine: Engine, from_state: str, to_state: str, risk_tier: int) -> None:
    allowed = list_allowed_states(engine)
    if to_state not in allowed:
        raise WorkflowError(f"Invalid to_state '{to_state}'. Allowed: {sorted(allowed)}")
    if from_state == to_state:
        raise WorkflowError("No-op transition (from_state == to_state) is not allowed")
