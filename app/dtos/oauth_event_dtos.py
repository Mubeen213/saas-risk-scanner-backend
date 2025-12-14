from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateOAuthEventDTO(BaseModel):
    organization_id: int
    connection_id: int
    user_id: int
    app_id: int
    event_type: str
    event_time: datetime
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OAuthEventResponseDTO(BaseModel):
    id: int
    organization_id: int
    user_id: int
    app_id: int
    event_type: str
    event_time: datetime
    actor_email: str | None = None
    actor_name: str | None = None
    actor_avatar_url: str | None = None
