from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateOAuthAppDTO(BaseModel):
    organization_id: int
    connection_id: int
    client_id: str
    name: str
    risk_score: int = 0
    is_system_app: bool = False
    is_trusted: bool = False
    scopes_summary: list[str] = Field(default_factory=list)
    image_url: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OAuthAppResponseDTO(BaseModel):
    id: int
    organization_id: int
    connection_id: int
    client_id: str
    name: str
    risk_score: int
    is_system_app: bool
    is_trusted: bool
    scopes_summary: list[str]
    image_url: str | None
    created_at: datetime
    updated_at: datetime


class OAuthAppWithStatsDTO(OAuthAppResponseDTO):
    active_grants_count: int = 0
    last_activity_at: datetime | None = None
