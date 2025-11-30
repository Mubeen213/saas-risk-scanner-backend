# Workspace Data Display - Implementation Plan

This document outlines the phased implementation plan for displaying workspace sync data (apps, users, groups) on the frontend with corresponding backend APIs.

---

## Plan Overview

**Goal**: Build a comprehensive dashboard that displays workspace data (discovered apps, users, groups) with drill-down capabilities, statistics, and settings management.

**Key Features**:
1. Dashboard with summary statistics (total apps, users, distribution charts)
2. Tabbed navigation: Apps | Users | Groups
3. Drill-down views: App → Users, User → Apps, Group → Members
4. Settings page with sync controls and connection management
5. Conditional UI based on connection status

---

## Phase 1: Backend API Layer

### 1.1 New Schemas (`app/schemas/workspace.py`)

**Note**: Schemas are for API input/output ONLY. They are used in controllers to serialize responses. Services do NOT import or return schemas.

```python
from pydantic import BaseModel
from datetime import datetime
from app.schemas.common import PaginationResponse

# --- Response Schemas (used by controllers) ---

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

class ConnectionSettingsResponse(BaseModel):
    connection: ConnectionResponse | None
    can_sync: bool
    is_syncing: bool

# This handles the Query Parameters logic
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)
    search: Optional[str] = None
```

### 1.2 New DTOs for Aggregated/Joined Data (`app/dtos/workspace_dtos.py`)

Per architecture guidelines:
- **Models** = 1:1 mapping with database tables (entities)
- **DTOs** = Complex Read (Joined), Create, and Update objects

Since these are JOIN results / aggregated data, they belong in **dtos/**, not models/.

```python
from pydantic import BaseModel
from datetime import datetime

# --- Aggregated Stats DTO (computed values, not a table) ---

class WorkspaceStatsDTO(BaseModel):
    total_users: int
    total_groups: int
    total_apps: int
    active_authorizations: int
    last_sync_at: datetime | None

# --- List DTOs with aggregated counts (JOIN results) ---

class WorkspaceUserWithAppCountDTO(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    is_delegated_admin: bool
    status: str
    authorized_apps_count: int  # Aggregated from app_authorization

class WorkspaceGroupWithMemberCountDTO(BaseModel):
    id: int
    email: str
    name: str
    description: str | None
    direct_members_count: int  # Aggregated from group_membership

class DiscoveredAppWithUserCountDTO(BaseModel):
    id: int
    display_name: str | None
    client_id: str
    client_type: str | None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    scopes_count: int  # Computed from all_scopes array length
    authorized_users_count: int  # Aggregated from app_authorization

# --- Join DTOs for nested relationships ---

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

# --- Detail DTOs (entity + nested join data) ---

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

# --- Settings DTO (composite data) ---

class ConnectionSettingsDTO(BaseModel):
    connection_id: int | None
    status: str | None
    admin_email: str | None
    workspace_domain: str | None
    last_sync_completed_at: datetime | None
    last_sync_status: str | None
    can_sync: bool
    is_syncing: bool
```

### 1.3 New Service (`app/services/workspace_data_service.py`)

**IMPORTANT**: Services return **DTOs** for joined/aggregated data, **models** for single entity returns. Controllers transform DTOs/models → schemas.

```python
from app.dtos.workspace_dtos import (
    WorkspaceStatsDTO,
    WorkspaceUserWithAppCountDTO,
    WorkspaceGroupWithMemberCountDTO,
    DiscoveredAppWithUserCount,
    UserWithAuthorizations,
    AppWithAuthorizations,
    GroupWithMembers,
    ConnectionSettings,
)

class WorkspaceDataService:
    def __init__(
        self,
        connection_repository: IdentityProviderConnectionRepository,
        workspace_user_repository: WorkspaceUserRepository,
        workspace_group_repository: WorkspaceGroupRepository,
        discovered_app_repository: DiscoveredAppRepository,
        app_authorization_repository: AppAuthorizationRepository,
    ):
        self._connection_repo = connection_repository
        self._user_repo = workspace_user_repository
        self._group_repo = workspace_group_repository
        self._app_repo = discovered_app_repository
        self._auth_repo = app_authorization_repository

    async def get_workspace_stats(self, organization_id: int) -> WorkspaceStatsDTO:
        # Returns DTO (aggregated data)

    async def get_users_paginated(
        self, organization_id: int,params: UserFilterParams
    ) -> tuple[list[WorkspaceUserWithAppCountDTO], int]:
        # Returns (list of DTOs, total_count)

    async def get_user_with_authorizations(
        self, organization_id: int, user_id: int
    ) -> UserWithAuthorizationsDTO | None:
        # Returns DTO or None

    async def get_groups_paginated(
        self, organization_id: int,params: UserFilterParams
    ) -> tuple[list[WorkspaceGroupWithMemberCountDTO], int]:
        # Returns (list of DTOs, total_count)

    async def get_group_with_members(
        self, organization_id: int, group_id: int
    ) -> GroupWithMembersDTO | None:
        # Returns DTO or None

    async def get_apps_paginated(
        self, organization_id: int,params: UserFilterParams
    ) -> tuple[list[DiscoveredAppWithUserCountDTO], int]:
        # Returns (list of DTOs, total_count)

    async def get_app_with_authorizations(
        self, organization_id: int, app_id: int
    ) -> AppWithAuthorizationsDTO | None:
        # Returns DTO or None

    async def get_connection_settings(
        self, organization_id: int
    ) -> ConnectionSettingsDTO:
        # Returns DTO
```

### 1.4 Repository Extensions

**Add to existing repositories:**

**IMPORTANT**: Repositories return **DTOs** from `dtos/workspace_dtos.py` for joined/aggregated data, or **models** for single entity returns. Use JOINs to avoid N+1 queries.

| Repository | New Method | Returns |
|------------|------------|---------|
| `WorkspaceUserRepository` | `find_by_organization_paginated(org_id, page, size, search)` | `tuple[list[WorkspaceUserWithAppCountDTO], int]` |
| `WorkspaceUserRepository` | `count_by_organization(org_id)` | `int` |
| `WorkspaceUserRepository` | `find_with_authorizations(org_id, user_id)` | `UserWithAuthorizationsDTO | None` |
| `WorkspaceGroupRepository` | `find_by_organization_paginated(org_id, page, size, search)` | `tuple[list[WorkspaceGroupWithMemberCountDTO], int]` |
| `WorkspaceGroupRepository` | `count_by_organization(org_id)` | `int` |
| `WorkspaceGroupRepository` | `find_with_members(org_id, group_id)` | `GroupWithMembersDTO | None` |
| `DiscoveredAppRepository` | `find_by_organization_paginated(org_id, page, size, search)` | `tuple[list[DiscoveredAppWithUserCountDTO], int]` |
| `DiscoveredAppRepository` | `count_by_organization(org_id)` | `int` |
| `DiscoveredAppRepository` | `find_with_authorizations(org_id, app_id)` | `AppWithAuthorizationsDTO | None` |
| `AppAuthorizationRepository` | `count_active_by_organization(org_id)` | `int` |

**SQL Pattern for Avoiding N+1 (Example for users with app count):**
```sql
SELECT 
    wu.id, wu.email, wu.full_name, wu.avatar_url, 
    wu.is_admin, wu.is_delegated_admin, wu.status,
    COUNT(aa.id) FILTER (WHERE aa.status = 'active') as authorized_apps_count
FROM workspace_user wu
LEFT JOIN app_authorization aa ON aa.workspace_user_id = wu.id
WHERE wu.organization_id = :org_id
  AND (wu.email ILIKE :search OR wu.full_name ILIKE :search OR :search IS NULL)
GROUP BY wu.id
ORDER BY wu.email
LIMIT :page_size OFFSET :offset
```

### 1.5 New API Routes (`app/api/v1/workspace_routes.py`)

**Controller Pattern**: Controllers call services (which return models), then transform to schemas.

```python
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import CurrentUserDep, WorkspaceDataServiceDep
from app.schemas.workspace import (
    WorkspaceStatsResponse,
    WorkspaceUsersListResponse,
    WorkspaceUserListItemResponse,
    UserDetailResponse,
    # ... other schemas
)
from app.schemas.common import create_success_response, create_error_response, PaginationResponse
import math

router = APIRouter(prefix="/workspace", tags=["workspace"])

@router.get("/stats")
async def get_workspace_stats(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    # Service returns model
    stats: WorkspaceStatsDTO  = await service.get_workspace_stats(current_user.organization_id)
    
    # Transform model -> schema in controller
    response = WorkspaceStatsResponse(
        total_users=stats.total_users,
        total_groups=stats.total_groups,
        total_apps=stats.total_apps,
        active_authorizations=stats.active_authorizations,
        last_sync_at=stats.last_sync_at,
    )
    return create_success_response(data=response.model_dump())

@router.get("/users")
async def get_workspace_users(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
     params: PaginationParams = Depends()
):
    users, total = await service.get_users_paginated(
        current_user.organization_id, page, page_size, search
    )
    
    # Transform models -> schemas
    items = [WorkspaceUserListItemResponse.model_validate(user) for user in users]
    pagination = PaginationResponse(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
    
    response = WorkspaceUsersListResponse(items=items, pagination=pagination)
    return create_success_response(data=response.model_dump())

@router.get("/users/{user_id}")
async def get_workspace_user_detail(
    user_id: int,
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    user: UserWithAuthorizationsDTO  = await service.get_user_with_authorizations(
        current_user.organization_id, user_id
    )
    if not user:
        return create_error_response(
            code="NOT_FOUND",
            message="User not found",
            status_code=404,
        )
    
    response = UserDetailResponse.model_validate(user)
    return create_success_response(data=response.model_dump())

# Similar pattern for /groups, /groups/{id}, /apps, /apps/{id}, /settings, /disconnect
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workspace/stats` | GET | Get dashboard statistics |
| `/workspace/users` | GET | List users (paginated, searchable) |
| `/workspace/users/{user_id}` | GET | Get user detail with apps |
| `/workspace/groups` | GET | List groups (paginated, searchable) |
| `/workspace/groups/{group_id}` | GET | Get group detail with members |
| `/workspace/apps` | GET | List discovered apps (paginated, searchable) |
| `/workspace/apps/{app_id}` | GET | Get app detail with authorized users |
| `/workspace/settings` | GET | Get connection settings |
| `/workspace/disconnect` | POST | Disconnect workspace |

**Query Parameters for list endpoints:**
- `page: int = 1`
- `page_size: int = 25`
- `search: str | None = None`


### 1.6 Dependency Injection Updates (`app/core/dependencies.py`)

```python
def get_workspace_data_service(
    connection_repository: IdentityProviderConnectionRepository = Depends(get_identity_provider_connection_repository),
    workspace_user_repository: WorkspaceUserRepository = Depends(get_workspace_user_repository),
    workspace_group_repository: WorkspaceGroupRepository = Depends(get_workspace_group_repository),
    discovered_app_repository: DiscoveredAppRepository = Depends(get_discovered_app_repository),
    app_authorization_repository: AppAuthorizationRepository = Depends(get_app_authorization_repository),
) -> WorkspaceDataService:
    return WorkspaceDataService(
        connection_repository=connection_repository,
        workspace_user_repository=workspace_user_repository,
        workspace_group_repository=workspace_group_repository,
        discovered_app_repository=discovered_app_repository,
        app_authorization_repository=app_authorization_repository,
    )

WorkspaceDataServiceDep = Annotated[WorkspaceDataService, Depends(get_workspace_data_service)]
```

---

## Phase 2: Frontend API Layer

### 2.1 New Types (`src/types/workspace.ts`)

```typescript
export interface WorkspaceStats {
  total_users: number;
  total_groups: number;
  total_apps: number;
  active_authorizations: number;
  last_sync_at: string | null;
}

export interface WorkspaceUserListItem {
  id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  is_delegated_admin: boolean;
  status: string;
  authorized_apps_count: number;
}

export interface WorkspaceGroupListItem {
  id: number;
  email: string;
  name: string;
  description: string | null;
  direct_members_count: number;
}

export interface DiscoveredAppListItem {
  id: number;
  display_name: string | null;
  client_id: string;
  client_type: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
  scopes_count: number;
  authorized_users_count: number;
}

// Detail types for drill-down views
export interface UserAppAuthorization {
  app_id: number;
  app_name: string | null;
  client_id: string;
  scopes: string[];
  authorized_at: string;
  status: string;
}

export interface UserDetail {
  id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  status: string;
  org_unit_path: string | null;
  authorizations: UserAppAuthorization[];
}

export interface AppAuthorizationUser {
  user_id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  scopes: string[];
  authorized_at: string;
  status: string;
}

export interface AppDetail {
  id: number;
  display_name: string | null;
  client_id: string;
  client_type: string | null;
  status: string;
  all_scopes: string[];
  first_seen_at: string;
  last_seen_at: string;
  authorizations: AppAuthorizationUser[];
}

export interface GroupMember {
  user_id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: string;
}

export interface GroupDetail {
  id: number;
  email: string;
  name: string;
  description: string | null;
  direct_members_count: number;
  members: GroupMember[];
}

export interface ConnectionSettings {
  connection: ConnectionInfo | null;
  can_sync: boolean;
  is_syncing: boolean;
}
```

### 2.2 API Functions (`src/api/workspace.ts`)

```typescript
// Endpoint constants
export const WORKSPACE_ENDPOINTS = {
  STATS: "/workspace/stats",
  USERS: "/workspace/users",
  USER_DETAIL: (id: number) => `/workspace/users/${id}`,
  GROUPS: "/workspace/groups",
  GROUP_DETAIL: (id: number) => `/workspace/groups/${id}`,
  APPS: "/workspace/apps",
  APP_DETAIL: (id: number) => `/workspace/apps/${id}`,
  SETTINGS: "/workspace/settings",
  DISCONNECT: "/workspace/disconnect",
} as const;

// API functions
export const getWorkspaceStats = async (): Promise<ApiResponse<WorkspaceStats>>

export const getWorkspaceUsers = async (
  params: PaginationParams
): Promise<ApiResponse<PaginatedResponse<WorkspaceUserListItem>>>

export const getWorkspaceUserDetail = async (
  userId: number
): Promise<ApiResponse<UserDetail>>

export const getWorkspaceGroups = async (
  params: PaginationParams
): Promise<ApiResponse<PaginatedResponse<WorkspaceGroupListItem>>>

export const getWorkspaceGroupDetail = async (
  groupId: number
): Promise<ApiResponse<GroupDetail>>

export const getDiscoveredApps = async (
  params: PaginationParams
): Promise<ApiResponse<PaginatedResponse<DiscoveredAppListItem>>>

export const getDiscoveredAppDetail = async (
  appId: number
): Promise<ApiResponse<AppDetail>>

export const getConnectionSettings = async (): Promise<ApiResponse<ConnectionSettings>>

export const disconnectWorkspace = async (): Promise<ApiResponse<void>>
```

---

## Phase 3: Frontend UI Components & Pages

### 3.1 Component Structure

```
src/
├── components/
│   ├── workspace/
│   │   ├── StatsCard.tsx            # Single stat display card
│   │   ├── StatsGrid.tsx            # Grid of StatsCards
│   │   ├── WorkspaceTabs.tsx        # Tab navigation (Apps|Users|Groups)
│   │   ├── ConnectWorkspaceCTA.tsx  # Connect button + description
│   │   ├── UserListItem.tsx         # User row in list
│   │   ├── GroupListItem.tsx        # Group row in list
│   │   ├── AppListItem.tsx          # App row in list
│   │   ├── UserDetailModal.tsx      # User detail with apps
│   │   ├── GroupDetailModal.tsx     # Group detail with members
│   │   └── AppDetailModal.tsx       # App detail with users
│   └── settings/
│       └── SyncControls.tsx         # Sync button + status
```

### 3.2 Page Structure

```
src/pages/
├── dashboard/
│   └── DashboardPage.tsx            # Refactored: stats + tabs + content
├── workspace/
│   ├── UsersPage.tsx                # Full-page user list (optional)
│   ├── GroupsPage.tsx               # Full-page group list (optional)
│   └── AppsPage.tsx                 # Full-page app list (optional)
└── settings/
    └── SettingsPage.tsx             # Connection management + sync
```

### 3.3 Dashboard Layout Redesign

**Updated `DashboardLayout.tsx` Sidebar:**

```tsx
// Navigation items
const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Settings, label: "Settings", path: "/settings" },
];
```

**Dashboard Page States:**

1. **No Connection State**: Show `ConnectWorkspaceCTA`, disable tabs
2. **Connected State**: Show stats grid + tabs (Apps | Users | Groups)
3. **Syncing State**: Show sync progress indicator

### 3.4 Dashboard Page Flow

```
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD (Connected)                                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ 127      │  │ 24       │  │ 45       │  │ 312          │ │
│  │ Users    │  │ Groups   │  │ Apps     │  │ Authorizations│ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [ Apps ✓ ]  [ Users ]  [ Groups ]                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ App Name          │ Type   │ Users │ First Seen │ ▶    ││
│  │ Slack             │ Native │ 89    │ Nov 15     │ ▶    ││
│  │ Zoom              │ Native │ 127   │ Nov 10     │ ▶    ││
│  │ Unknown App       │ Web    │ 12    │ Nov 28     │ ▶    ││
│  └─────────────────────────────────────────────────────────┘│
│                              [1] [2] [3] ... [10]           │
└─────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD (Not Connected)                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  🔗 Connect Your Workspace               ││
│  │                                                          ││
│  │   Connect your Google Workspace to discover all         ││
│  │   third-party apps and OAuth permissions.               ││
│  │                                                          ││
│  │              [ Connect Google Workspace ]                ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  (Grayed out)    │
│  │ --       │  │ --       │  │ --       │                   │
│  │ Users    │  │ Groups   │  │ Apps     │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│                                                             │
│  [ Apps ]  [ Users ]  [ Groups ]  (Disabled)                │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Settings Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  SETTINGS                                                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Workspace Connection                                    ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  Status: ● Connected (Active)                            ││
│  │  Admin: admin@company.com                                ││
│  │  Domain: company.com                                     ││
│  │  Last Sync: Dec 1, 2025, 10:30 AM                       ││
│  │                                                          ││
│  │  [ Sync Now ]    [ Disconnect Workspace ]               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Sync History                                            ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  • Dec 1, 10:30 AM - Completed (127 users, 45 apps)     ││
│  │  • Nov 30, 10:30 AM - Completed (125 users, 44 apps)    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 3.6 Drill-Down Modal Examples

**App Detail Modal:**
```
┌────────────────────────────────────────────────┐
│  Slack                                    [X]  │
├────────────────────────────────────────────────┤
│  Client ID: 1234567890.apps.slack.com          │
│  Type: Native                                  │
│  First Seen: Nov 15, 2025                      │
│  Scopes: 12                                    │
│                                                │
│  Authorized Users (89)                         │
│  ┌──────────────────────────────────────────┐  │
│  │ User                    │ Authorized     │  │
│  │ john@company.com        │ Nov 15, 2025   │  │
│  │ jane@company.com        │ Nov 16, 2025   │  │
│  │ ...                                      │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## Phase 4: Routing & Navigation

### 4.1 Route Structure

```typescript
// App.tsx routes
{
  path: "/",
  element: <ProtectedRoute><DashboardLayout /></ProtectedRoute>,
  children: [
    { path: "dashboard", element: <DashboardPage /> },
    { path: "settings", element: <SettingsPage /> },
    // Optional dedicated pages
    { path: "workspace/users", element: <UsersPage /> },
    { path: "workspace/groups", element: <GroupsPage /> },
    { path: "workspace/apps", element: <AppsPage /> },
  ],
}
```

### 4.2 Navigation Config

```typescript
// config/navigation.ts
export const NAV_ITEMS = [
  { icon: "LayoutDashboard", label: "Dashboard", path: "/dashboard" },
  { icon: "Settings", label: "Settings", path: "/settings" },
];
```

---

## Implementation Order

### Phase 1: Backend (Priority: High)
1. Create `app/dtos/workspace_dtos.py` with aggregated/joined DTOs
2. Create `app/schemas/workspace.py` with all response schemas
3. Add paginated + aggregated methods to existing repositories (using JOINs, returning DTOs)
4. Create `app/services/workspace_data_service.py` (returns DTOs for joined data)
5. Add DI wiring in `dependencies.py`
6. Create `app/api/v1/workspace_routes.py` (transforms DTOs → schemas)
7. Register router in `app/api/v1/__init__.py`

### Phase 2: Frontend API (Priority: High)
1. Create `src/types/workspace.ts`
2. Create `src/api/workspace.ts`
3. Update `src/constants/api.ts` with new endpoints

### Phase 3: Frontend UI - Core (Priority: High)
1. Create `src/components/workspace/` directory
2. Build `StatsCard`, `StatsGrid` components
3. Build `WorkspaceTabs` component
4. Build `ConnectWorkspaceCTA` component
5. Refactor `DashboardPage.tsx`
6. Update `DashboardLayout.tsx` with sidebar nav

### Phase 4: Frontend UI - Lists (Priority: Medium)
1. Build `AppListItem`, `UserListItem`, `GroupListItem`
2. Build list views within tabs
3. Add pagination component
4. Add search/filter functionality

### Phase 5: Frontend UI - Details (Priority: Medium)
1. Build `AppDetailModal`
2. Build `UserDetailModal`
3. Build `GroupDetailModal`

### Phase 6: Settings Page (Priority: Medium)
1. Create `src/pages/settings/SettingsPage.tsx`
2. Build sync controls and connection management
3. Add route and navigation

---

## API Response Examples

### GET /workspace/stats
```json
{
  "meta": { "request_id": "...", "timestamp": "..." },
  "data": {
    "total_users": 127,
    "total_groups": 24,
    "total_apps": 45,
    "active_authorizations": 312,
    "last_sync_at": "2025-12-01T10:30:00Z"
  },
  "error": null
}
```

### GET /workspace/apps?page=1&page_size=25
```json
{
  "meta": { "request_id": "...", "timestamp": "..." },
  "data": {
    "items": [
      {
        "id": 1,
        "display_name": "Slack",
        "client_id": "1234567890.apps.slack.com",
        "client_type": "native",
        "status": "active",
        "first_seen_at": "2025-11-15T08:00:00Z",
        "last_seen_at": "2025-12-01T10:00:00Z",
        "scopes_count": 12,
        "authorized_users_count": 89
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 25,
      "total_items": 45,
      "total_pages": 2
    }
  },
  "error": null
}
```

### GET /workspace/apps/1
```json
{
  "meta": { "request_id": "...", "timestamp": "..." },
  "data": {
    "id": 1,
    "display_name": "Slack",
    "client_id": "1234567890.apps.slack.com",
    "client_type": "native",
    "status": "active",
    "all_scopes": ["openid", "email", "profile", "..."],
    "first_seen_at": "2025-11-15T08:00:00Z",
    "last_seen_at": "2025-12-01T10:00:00Z",
    "authorizations": [
      {
        "user_id": 1,
        "email": "john@company.com",
        "full_name": "John Doe",
        "avatar_url": "https://...",
        "scopes": ["openid", "email"],
        "authorized_at": "2025-11-15T08:00:00Z",
        "status": "active"
      }
    ]
  },
  "error": null
}
```

---

## Further Considerations

1. **Polling vs Real-time**: Should stats auto-refresh? Consider polling every 30s or after sync completes.

2. **Caching Strategy**: Cache stats on backend (TTL: 60s) to avoid repeated count queries?

3. **Disconnect Flow**: When disconnecting, should we delete synced data or keep it read-only?
