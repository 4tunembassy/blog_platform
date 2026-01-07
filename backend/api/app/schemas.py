# backend/api/app/schemas.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContentCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    risk_tier: int = Field(1, ge=1, le=3)  # clamp to enum reality


class ContentOut(BaseModel):
    id: str
    title: str
    state: str
    risk_tier: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AllowedTransitionOut(BaseModel):
    content_id: str
    from_state: str
    risk_tier: int
    allowed: List[str]


class EventOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: Optional[str] = None
    payload: Dict[str, Any]
    created_at: Optional[str] = None
