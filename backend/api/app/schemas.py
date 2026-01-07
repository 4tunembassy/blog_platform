from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# --------- Core DTOs ---------

class ContentCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    risk_tier: int = Field(1, ge=1, le=4)


class ContentOut(BaseModel):
    id: str
    title: str
    state: str
    risk_tier: int
    created_at: str
    updated_at: str


class ContentListOut(BaseModel):
    items: List[ContentOut]
    limit: int
    offset: int
    total: int


class AllowedTransitionsOut(BaseModel):
    content_id: str
    from_state: str
    risk_tier: int
    allowed: List[str]


class TransitionIn(BaseModel):
    to_state: str = Field(..., min_length=1, max_length=50)


class TransitionOut(BaseModel):
    content_id: str
    from_state: str
    to_state: str
    risk_tier: int


class EventOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: Optional[str] = None
    payload: dict
    created_at: str


# --------- Query types ---------

SortKey = Literal["created_at_desc", "created_at_asc"]
