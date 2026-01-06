@'
from __future__ import annotations

# These are your DB enum values (public.content_state).
# Keep in sync with: SELECT unnest(enum_range(NULL::content_state))::text;
STATES: list[str] = [
    "INGESTED",
    "CLASSIFIED",
    "SELECTED",
    "RESEARCHED",
    "DRAFTED",
    "VALIDATED",
    "PENDING_APPROVAL",
    "READY_TO_PUBLISH",
    "PUBLISHED",
    "DEFERRED",
    "RETIRED",
]


class WorkflowError(Exception):
    pass


def list_states() -> list[str]:
    return list(STATES)


# Minimal policy for now (Tier1+ same for demo). We'll refine later.
TRANSITIONS: dict[str, list[str]] = {
    "INGESTED": ["CLASSIFIED", "DEFERRED", "RETIRED"],
    "CLASSIFIED": ["SELECTED", "DEFERRED", "RETIRED"],
    "SELECTED": ["RESEARCHED", "DEFERRED", "RETIRED"],
    "RESEARCHED": ["DRAFTED", "DEFERRED", "RETIRED"],
    "DRAFTED": ["VALIDATED", "DEFERRED", "RETIRED"],
    "VALIDATED": ["PENDING_APPROVAL", "DEFERRED", "RETIRED"],
    "PENDING_APPROVAL": ["READY_TO_PUBLISH", "DEFERRED", "RETIRED"],
    "READY_TO_PUBLISH": ["PUBLISHED", "DEFERRED", "RETIRED"],
    "PUBLISHED": ["RETIRED"],
    "DEFERRED": ["CLASSIFIED", "RETIRED"],
    "RETIRED": [],
}


def allowed_transitions(from_state: str, risk_tier: int) -> list[str]:
    # risk_tier reserved for future gating
    return TRANSITIONS.get(from_state, [])


def validate_transition(from_state: str, to_state: str, risk_tier: int) -> None:
    if to_state not in STATES:
        raise WorkflowError(f"Unknown state: {to_state}")

    allowed = allowed_transitions(from_state, risk_tier)
    if to_state not in allowed:
        raise WorkflowError(f"Invalid transition: {from_state} -> {to_state}. Allowed: {allowed}")
'@ | Set-Content -Encoding utf8 .\backend\api\app\workflow.py
