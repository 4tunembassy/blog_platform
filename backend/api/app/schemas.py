from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

class ContentCreateIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    risk_tier: int = Field(default=1, ge=1, le=3)

class ContentOut(BaseModel):
    id: str
    title: str
    state: str
    risk_tier: int
    created_at: datetime
    updated_at: datetime

class TransitionIn(BaseModel):
    to_state: str = Field(min_length=2, max_length=50)
    reason: str = Field(default="", max_length=500)
    actor_type: str = Field(default="system", max_length=50)
    actor_id: str | None = Field(default=None, max_length=200)

class EventOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: str | None
    payload: dict
    created_at: datetime
