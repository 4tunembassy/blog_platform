from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ContentCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    risk_tier: int = Field(..., ge=1, le=10)


class TransitionIn(BaseModel):
    to_state: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=2000)
    actor_type: str = Field(..., min_length=1, max_length=50)
    actor_id: str | None = Field(default=None, max_length=200)


class ContentOut(BaseModel):
    id: str
    title: str
    state: str
    risk_tier: int
    created_at: str
    updated_at: str


class EventOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: str | None = None
    payload: dict[str, Any]
    created_at: str


# -------------------------
# Step 4: Provenance
# -------------------------
class ProvenanceOut(BaseModel):
    id: str
    tenant_id: str
    content_id: str | None = None
    intake_id: str | None = None
    agent_name: str
    prompt_version_id: str | None = None
    policy_version_id: str | None = None
    model_name: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    status: str
    details: dict[str, Any]
    created_at: str
