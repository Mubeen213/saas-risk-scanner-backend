from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int
    provider_group_id: str
    email: str
    name: str
    description: str | None = None
    direct_members_count: int = 0
    raw_data: dict[str, Any] = Field(default_factory=dict)
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime
