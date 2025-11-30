from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginationResponse


class WorkspaceStatsResponse(BaseModel):
    total_users: int
    total_groups: int
    total_apps: int
    active_authorizations: int
    last_sync_at: datetime | None


class WorkspaceUserListItemResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    is_delegated_admin: bool
    status: str
    authorized_apps_count: int


class WorkspaceUsersListResponse(BaseModel):
    items: list[WorkspaceUserListItemResponse]
    pagination: PaginationResponse


class WorkspaceGroupListItemResponse(BaseModel):
    id: int
    email: str
    name: str
    description: str | None
    direct_members_count: int


class WorkspaceGroupsListResponse(BaseModel):
    items: list[WorkspaceGroupListItemResponse]
    pagination: PaginationResponse


class DiscoveredAppListItemResponse(BaseModel):
    id: int
    display_name: str | None
    client_id: str
    client_type: str | None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    scopes_count: int
    authorized_users_count: int


class DiscoveredAppsListResponse(BaseModel):
    items: list[DiscoveredAppListItemResponse]
    pagination: PaginationResponse


class UserAppAuthorizationItemResponse(BaseModel):
    app_id: int
    app_name: str | None
    client_id: str
    scopes: list[str]
    authorized_at: datetime
    status: str


class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    status: str
    org_unit_path: str | None
    authorizations: list[UserAppAuthorizationItemResponse]


class AppAuthorizationUserItemResponse(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    scopes: list[str]
    authorized_at: datetime
    status: str


class AppDetailResponse(BaseModel):
    id: int
    display_name: str | None
    client_id: str
    client_type: str | None
    status: str
    all_scopes: list[str]
    first_seen_at: datetime
    last_seen_at: datetime
    authorizations: list[AppAuthorizationUserItemResponse]


class GroupMemberItemResponse(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str


class GroupDetailResponse(BaseModel):
    id: int
    email: str
    name: str
    description: str | None
    direct_members_count: int
    members: list[GroupMemberItemResponse]


class ConnectionInfoResponse(BaseModel):
    connection_id: int
    status: str
    admin_email: str | None
    workspace_domain: str | None
    last_sync_completed_at: datetime | None
    last_sync_status: str | None


class ConnectionSettingsResponse(BaseModel):
    connection: ConnectionInfoResponse | None
    can_sync: bool
    is_syncing: bool


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)
    search: Optional[str] = None
