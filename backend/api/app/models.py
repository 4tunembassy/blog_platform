from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

@dataclass(frozen=True)
class ContentItem:
    id: str
    title: str
    state: str
    risk_tier: int
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class ProvenanceEvent:
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_type: str
    actor_id: Optional[str]
    payload: dict[str, Any]
    created_at: datetime
