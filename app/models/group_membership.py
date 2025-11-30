from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GroupMembership(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_user_id: int
    workspace_group_id: int
    role: str
    created_at: datetime
