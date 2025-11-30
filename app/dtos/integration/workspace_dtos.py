from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateWorkspaceUserDTO(BaseModel):
    organization_id: int = Field(..., gt=0)
    connection_id: int = Field(..., gt=0)
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


class UpdateWorkspaceUserDTO(BaseModel):
    email: str | None = None
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    is_admin: bool | None = None
    is_delegated_admin: bool | None = None
    status: str | None = None
    org_unit_path: str | None = None
    avatar_url: str | None = None
    raw_data: dict[str, Any] | None = None
    last_synced_at: datetime | None = None


class CreateWorkspaceGroupDTO(BaseModel):
    organization_id: int = Field(..., gt=0)
    connection_id: int = Field(..., gt=0)
    provider_group_id: str
    email: str
    name: str
    description: str | None = None
    direct_members_count: int = 0
    raw_data: dict[str, Any] = Field(default_factory=dict)


class UpdateWorkspaceGroupDTO(BaseModel):
    email: str | None = None
    name: str | None = None
    description: str | None = None
    direct_members_count: int | None = None
    raw_data: dict[str, Any] | None = None
    last_synced_at: datetime | None = None


class CreateGroupMembershipDTO(BaseModel):
    workspace_user_id: int = Field(..., gt=0)
    workspace_group_id: int = Field(..., gt=0)
    role: str = "MEMBER"
