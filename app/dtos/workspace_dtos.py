from datetime import datetime

from pydantic import BaseModel


class WorkspaceStatsDTO(BaseModel):
    total_users: int
    total_groups: int
    total_apps: int
    active_authorizations: int
    last_sync_at: datetime | None


class WorkspaceUserWithAppCountDTO(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    is_delegated_admin: bool
    status: str
    authorized_apps_count: int


class WorkspaceGroupWithMemberCountDTO(BaseModel):
    id: int
    email: str
    name: str
    description: str | None
    direct_members_count: int


class DiscoveredAppWithUserCountDTO(BaseModel):
    id: int
    display_name: str | None
    client_id: str
    client_type: str | None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    scopes_count: int
    authorized_users_count: int


class AuthorizationWithAppDTO(BaseModel):
    app_id: int
    app_name: str | None
    client_id: str
    scopes: list[str]
    authorized_at: datetime
    status: str


class AuthorizationWithUserDTO(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    scopes: list[str]
    authorized_at: datetime
    status: str


class GroupMemberWithUserDTO(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str


class UserWithAuthorizationsDTO(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    status: str
    org_unit_path: str | None
    authorizations: list[AuthorizationWithAppDTO]


class AppWithAuthorizationsDTO(BaseModel):
    id: int
    display_name: str | None
    client_id: str
    client_type: str | None
    status: str
    all_scopes: list[str]
    first_seen_at: datetime
    last_seen_at: datetime
    authorizations: list[AuthorizationWithUserDTO]


class GroupWithMembersDTO(BaseModel):
    id: int
    email: str
    name: str
    description: str | None
    direct_members_count: int
    members: list[GroupMemberWithUserDTO]


class ConnectionSettingsDTO(BaseModel):
    connection_id: int | None
    status: str | None
    admin_email: str | None
    workspace_domain: str | None
    last_sync_completed_at: datetime | None
    last_sync_status: str | None
    can_sync: bool
    is_syncing: bool


class PaginationParamsDTO(BaseModel):
    page: int = 1
    page_size: int = 25
    search: str | None = None
