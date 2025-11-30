from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int
    provider_user_id: str
    email: str
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    is_admin: bool = False
    is_delegated_admin: bool = False
    status: str
    org_unit_path: str | None = None
    avatar_url: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime
