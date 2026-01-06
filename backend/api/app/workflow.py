from __future__ import annotations

from dataclasses import dataclass

# DB enum values (confirmed from your Postgres enum_range output)
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
    """Raised when a workflow transition is invalid."""


def list_states() -> list[str]:
    return list(STATES)


# A simple, deterministic workflow graph.
# (You can tighten/expand rules later; this is stable and matches your enum set.)
_TRANSITIONS: dict[str, list[str]] = {
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


def _normalize_state(state: str) -> str:
    if not state:
        return state
    return state.strip().upper()


def _normalize_risk_tier(risk_tier: int) -> int:
    # Your API uses 1..3, DB uses enum risk_tier internally.
    # We keep the API contract: 1..3
    try:
        r = int(risk_tier)
    except Exception:
        raise WorkflowError("risk_tier must be an integer")
    if r < 1 or r > 3:
        raise WorkflowError("risk_tier must be between 1 and 3")
    return r


def allowed_transitions(from_state: str, risk_tier: int) -> list[str]:
    """
    Returns allowed next states from `from_state`.

    risk_tier is currently used as a hook for future policy gating.
    For now, it only validates 1..3 to keep the system consistent.
    """
    _ = _normalize_risk_tier(risk_tier)
    s = _normalize_state(from_state)

    if s not in _TRANSITIONS:
        # If DB ever returns a new state, don't crash hard; just return no transitions.
        return []
    return list(_TRANSITIONS[s])


def validate_transition(from_state: str, to_state: str, risk_tier: int) -> None:
    """
    Raises WorkflowError if the transition is not permitted.
    """
    s_from = _normalize_state(from_state)
    s_to = _normalize_state(to_state)
    r = _normalize_risk_tier(risk_tier)

    if s_from not in STATES:
        raise WorkflowError(f"Unknown from_state: {from_state}")

    if s_to not in STATES:
        raise WorkflowError(f"Unknown to_state: {to_state}")

    allowed = allowed_transitions(s_from, r)
    if s_to not in allowed:
        raise WorkflowError(f"Transition not allowed: {s_from} -> {s_to}. Allowed: {allowed}")
