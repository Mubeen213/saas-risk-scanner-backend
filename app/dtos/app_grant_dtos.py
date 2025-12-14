from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateAppGrantDTO(BaseModel):
    organization_id: int
    connection_id: int
    user_id: int
    app_id: int
    status: str
    scopes: list[str] = Field(default_factory=list)
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    last_accessed_at: datetime | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class AppGrantResponseDTO(BaseModel):
    id: int
    organization_id: int
    connection_id: int
    user_id: int
    app_id: int
    status: str
    scopes: list[str]
    granted_at: datetime | None
    revoked_at: datetime | None
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime
