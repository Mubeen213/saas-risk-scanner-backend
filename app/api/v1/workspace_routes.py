import logging
import math

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUserDep, WorkspaceDataServiceDep
from app.dtos.workspace_dtos import PaginationParamsDTO
from app.schemas.common import (
    ApiResponse,
    PaginationResponse,
    create_error_response,
    create_success_response,
)
from app.schemas.workspace import (
    AppDetailResponse,
    AppAuthorizationUserItemResponse,
    ConnectionInfoResponse,
    ConnectionSettingsResponse,
    DiscoveredAppsListResponse,
    GroupDetailResponse,
    OAuthAppListItemResponse,
    GroupMemberItemResponse,
    UserAppAuthorizationItemResponse,
    UserDetailResponse,
    WorkspaceGroupListItemResponse,
    WorkspaceGroupsListResponse,
    WorkspaceStatsResponse,
    WorkspaceUserListItemResponse,
    WorkspaceUsersListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/stats", response_model=ApiResponse)
async def get_workspace_stats(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    stats = await service.get_workspace_stats(current_user.organization_id)
    response = WorkspaceStatsResponse(
        total_users=stats.total_users,
        total_groups=stats.total_groups,
        total_apps=stats.total_apps,
        active_authorizations=stats.active_authorizations,
        last_sync_at=stats.last_sync_at,
    )
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/users", response_model=ApiResponse)
async def get_workspace_users(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
):
    params = PaginationParamsDTO(page=page, page_size=page_size, search=search)
    users, total = await service.get_users_paginated(
        current_user.organization_id, params
    )

    items = [
        WorkspaceUserListItemResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_admin=user.is_admin,
            is_delegated_admin=user.is_delegated_admin,
            status=user.status,
            authorized_apps_count=user.authorized_apps_count,
        )
        for user in users
    ]
    pagination = PaginationResponse(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
    response = WorkspaceUsersListResponse(items=items, pagination=pagination)
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/users/{user_id}", response_model=ApiResponse)
async def get_workspace_user_detail(
    user_id: int,
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    logger.debug(
        f"Fetching details for user_id={user_id} and organization_id={current_user.organization_id}"
    )
    user = await service.get_user_with_authorizations(
        current_user.organization_id, user_id
    )
    if not user:
        return create_error_response(
            code="NOT_FOUND",
            message="User not found",
            status_code=404,
        )

    authorizations = [
        UserAppAuthorizationItemResponse(
            app_id=auth.app_id,
            app_name=auth.app_name,
            client_id=auth.client_id,
            scopes=auth.scopes,
            authorized_at=auth.authorized_at,
            status=auth.status,
        )
        for auth in user.authorizations
    ]
    response = UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        status=user.status,
        org_unit_path=user.org_unit_path,
        authorizations=authorizations,
    )
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/groups", response_model=ApiResponse)
async def get_workspace_groups(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
):
    params = PaginationParamsDTO(page=page, page_size=page_size, search=search)
    groups, total = await service.get_groups_paginated(
        current_user.organization_id, params
    )

    items = [
        WorkspaceGroupListItemResponse(
            id=group.id,
            email=group.email,
            name=group.name,
            description=group.description,
            direct_members_count=group.direct_members_count,
        )
        for group in groups
    ]
    pagination = PaginationResponse(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
    response = WorkspaceGroupsListResponse(items=items, pagination=pagination)
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/groups/{group_id}", response_model=ApiResponse)
async def get_workspace_group_detail(
    group_id: int,
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    group = await service.get_group_with_members(current_user.organization_id, group_id)
    if not group:
        return create_error_response(
            code="NOT_FOUND",
            message="Group not found",
            status_code=404,
        )

    members = [
        GroupMemberItemResponse(
            user_id=member.user_id,
            email=member.email,
            full_name=member.full_name,
            avatar_url=member.avatar_url,
            role=member.role,
        )
        for member in group.members
    ]
    response = GroupDetailResponse(
        id=group.id,
        email=group.email,
        name=group.name,
        description=group.description,
        direct_members_count=group.direct_members_count,
        members=members,
    )
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/apps", response_model=ApiResponse)
async def get_discovered_apps(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
):
    params = PaginationParamsDTO(page=page, page_size=page_size, search=search)
    apps, total = await service.get_apps_paginated(current_user.organization_id, params)

    items = [
        OAuthAppListItemResponse(
            id=app.id,
            name=app.name,
            client_id=app.client_id,
            risk_score=app.risk_score,
            is_system_app=app.is_system_app,
            is_trusted=app.is_trusted,
            scopes_summary=app.scopes_summary,
            active_grants_count=app.active_grants_count,
            last_activity_at=app.last_activity_at,
        )
        for app in apps
    ]
    pagination = PaginationResponse(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
    response = DiscoveredAppsListResponse(items=items, pagination=pagination)
    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/apps/{app_id}", response_model=ApiResponse)
async def get_discovered_app_detail(
    app_id: int,
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    app = await service.get_app_with_authorizations(
        current_user.organization_id, app_id
    )
    if not app:
        return create_error_response(
            code="NOT_FOUND",
            message="App not found",
            status_code=404,
        )

    authorizations = [
        AppAuthorizationUserItemResponse(
            user_id=auth.user_id,
            email=auth.email,
            full_name=auth.full_name,
            avatar_url=auth.avatar_url,
            scopes=auth.scopes,
            authorized_at=auth.authorized_at,
            status=auth.status,
        )
        for auth in app.authorizations
    ]

    response = AppDetailResponse(
        id=app.id,
        name=app.name,
        client_id=app.client_id,
        client_type=None,
        status=app.status,
        risk_score=app.risk_score,
        is_system_app=app.is_system_app,
        is_trusted=app.is_trusted,
        all_scopes=app.all_scopes,
        active_grants_count=app.active_grants_count,
        last_activity_at=app.last_activity_at,
        authorizations=authorizations,
    )

    return create_success_response(data=response.model_dump(mode="json"))


@router.get("/apps/{app_id}/timeline", response_model=ApiResponse)
async def get_app_timeline(
    app_id: int,
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    params = PaginationParamsDTO(page=page, page_size=page_size)
    events, total = await service.get_app_timeline(
        current_user.organization_id, app_id, params
    )
    
    pagination = PaginationResponse(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
    
    return create_success_response(
        data={
            "items": [e.model_dump(mode="json") for e in events],
            "pagination": pagination.model_dump(mode="json") 
        }
    )


@router.get("/settings", response_model=ApiResponse)
async def get_connection_settings(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    settings_dto = await service.get_connection_settings(current_user.organization_id)

    connection_info = None
    if settings_dto.connection_id:
        connection_info = ConnectionInfoResponse(
            connection_id=settings_dto.connection_id,
            status=settings_dto.status,
            admin_email=settings_dto.admin_email,
            workspace_domain=settings_dto.workspace_domain,
            last_sync_completed_at=settings_dto.last_sync_completed_at,
            last_sync_status=settings_dto.last_sync_status,
        )

    response = ConnectionSettingsResponse(
        connection=connection_info,
        can_sync=settings_dto.can_sync,
        is_syncing=settings_dto.is_syncing,
    )
    return create_success_response(data=response.model_dump(mode="json"))


@router.post("/disconnect", response_model=ApiResponse)
async def disconnect_workspace(
    current_user: CurrentUserDep,
    service: WorkspaceDataServiceDep,
):
    success = await service.disconnect_workspace(current_user.organization_id)
    if not success:
        return create_error_response(
            code="NOT_FOUND",
            message="No active workspace connection found",
            status_code=404,
        )
    return create_success_response(data={"disconnected": True})
