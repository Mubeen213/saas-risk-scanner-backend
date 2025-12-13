from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AppGrant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int

    user_id: int  # References identity_user(id) / workspace_user(id)
    app_id: int   # References oauth_app(id)

    status: str = "active"
    scopes: list[str] = Field(default_factory=list)

    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    last_accessed_at: datetime | None = None

    raw_data: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime
