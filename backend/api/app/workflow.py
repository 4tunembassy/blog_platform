from __future__ import annotations

class WorkflowError(Exception):
    pass

STATES = [
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

HAPPY_PATH = {
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

def validate_risk_tier(risk_tier: int) -> None:
    if not isinstance(risk_tier, int):
        raise WorkflowError("risk_tier must be an integer")
    if risk_tier < 1 or risk_tier > 3:
        raise WorkflowError("risk_tier must be between 1 and 3")

def allowed_transitions(from_state: str, risk_tier: int) -> list[str]:
    validate_risk_tier(risk_tier)
    if from_state not in STATES:
        return []
    return HAPPY_PATH.get(from_state, [])

def validate_transition(from_state: str, to_state: str, risk_tier: int) -> None:
    if to_state not in STATES:
        raise WorkflowError(f"Unknown to_state: {to_state}")
    allowed = allowed_transitions(from_state, risk_tier)
    if to_state not in allowed:
        raise WorkflowError(f"Invalid transition {from_state} -> {to_state}")
