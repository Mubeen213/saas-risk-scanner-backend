from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AppAuthorization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discovered_app_id: int
    workspace_user_id: int
    scopes: list[str] = Field(default_factory=list)
    status: str
    authorized_at: datetime
    revoked_at: datetime | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
