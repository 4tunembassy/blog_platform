from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


ContentState = Literal["INGESTED", "CLASSIFIED", "DEFERRED", "RETIRED"]


class ContentCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=400)
    risk_tier: int = Field(1, ge=1, le=3, description="Risk tier 1..3 (DB enum supports TIER_1..TIER_3)")


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    state: ContentState
    risk_tier: int
    created_at: datetime
    updated_at: datetime


class ContentListOut(BaseModel):
    items: List[ContentOut]
    limit: int
    offset: int
    total: int


class AllowedTransitionsOut(BaseModel):
    content_id: str
    from_state: ContentState
    risk_tier: int
    allowed: List[ContentState]


class EventOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: Optional[str] = None
    payload: Dict[str, Any]
    created_at: datetime


class TransitionIn(BaseModel):
    to_state: ContentState


class TransitionOut(BaseModel):
    content_id: str
    from_state: ContentState
    to_state: ContentState
    risk_tier: int
