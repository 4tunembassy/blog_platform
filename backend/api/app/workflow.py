from __future__ import annotations

class WorkflowError(ValueError):
    pass

STATES = {
    "intake",
    "classified",
    "researched",
    "drafted",
    "review_needed",
    "approved",
    "published",
    "archived",
}

# Allowed transitions depend on tier (1 or 2). Tier 3 is restricted in MVP.
ALLOWED_TIER1 = {
    "intake": {"classified"},
    "classified": {"researched"},
    "researched": {"drafted"},
    "drafted": {"published"},
    "published": {"archived"},
}

ALLOWED_TIER2 = {
    "intake": {"classified"},
    "classified": {"researched"},
    "researched": {"drafted"},
    "drafted": {"review_needed"},
    "review_needed": {"approved", "drafted"},  # allow revise
    "approved": {"published"},
    "published": {"archived"},
}

def validate_transition(from_state: str, to_state: str, risk_tier: int) -> None:
    if from_state not in STATES:
        raise WorkflowError(f"Unknown from_state: {from_state}")
    if to_state not in STATES:
        raise WorkflowError(f"Unknown to_state: {to_state}")

    if risk_tier == 1:
        allowed = ALLOWED_TIER1
    elif risk_tier == 2:
        allowed = ALLOWED_TIER2
    else:
        raise WorkflowError("Tier 3 content is restricted in MVP.")

    if to_state not in allowed.get(from_state, set()):
        raise WorkflowError(f"Invalid transition {from_state} -> {to_state} for tier {risk_tier}")
