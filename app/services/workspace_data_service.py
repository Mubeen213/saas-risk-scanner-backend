import logging

from app.dtos.workspace_dtos import (
    AppWithAuthorizationsDTO,
    ConnectionSettingsDTO,
    DiscoveredAppWithUserCountDTO,
    GroupWithMembersDTO,
    PaginationParamsDTO,
    UserWithAuthorizationsDTO,
    WorkspaceGroupWithMemberCountDTO,
    WorkspaceStatsDTO,
    WorkspaceUserWithAppCountDTO,
)
from app.repositories.app_authorization_repository import AppAuthorizationRepository
from app.repositories.discovered_app_repository import DiscoveredAppRepository
from app.repositories.identity_provider_connection_repository import (
    IdentityProviderConnectionRepository,
)
from app.repositories.workspace_group_repository import WorkspaceGroupRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository

logger = logging.getLogger(__name__)


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
        total_users = await self._user_repo.count_by_organization(organization_id)
        total_groups = await self._group_repo.count_by_organization(organization_id)
        total_apps = await self._app_repo.count_by_organization(organization_id)
        active_authorizations = await self._auth_repo.count_active_by_organization(
            organization_id
        )

        connections = await self._connection_repo.find_by_organization(organization_id)
        last_sync_at = None
        if connections:
            active_connection = next(
                (c for c in connections if c.status == "active"), None
            )
            if active_connection:
                last_sync_at = active_connection.last_sync_completed_at

        return WorkspaceStatsDTO(
            total_users=total_users,
            total_groups=total_groups,
            total_apps=total_apps,
            active_authorizations=active_authorizations,
            last_sync_at=last_sync_at,
        )

    async def get_users_paginated(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[WorkspaceUserWithAppCountDTO], int]:
        return await self._user_repo.find_paginated_with_app_count(
            organization_id, params
        )

    async def get_user_with_authorizations(
        self, organization_id: int, user_id: int
    ) -> UserWithAuthorizationsDTO | None:
        return await self._user_repo.find_with_authorizations(organization_id, user_id)

    async def get_groups_paginated(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[WorkspaceGroupWithMemberCountDTO], int]:
        return await self._group_repo.find_paginated_with_member_count(
            organization_id, params
        )

    async def get_group_with_members(
        self, organization_id: int, group_id: int
    ) -> GroupWithMembersDTO | None:
        return await self._group_repo.find_with_members(organization_id, group_id)

    async def get_apps_paginated(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[DiscoveredAppWithUserCountDTO], int]:
        return await self._app_repo.find_paginated_with_user_count(
            organization_id, params
        )

    async def get_app_with_authorizations(
        self, organization_id: int, app_id: int
    ) -> AppWithAuthorizationsDTO | None:
        return await self._app_repo.find_with_authorizations(organization_id, app_id)

    async def get_connection_settings(
        self, organization_id: int
    ) -> ConnectionSettingsDTO:
        connections = await self._connection_repo.find_by_organization(organization_id)

        if not connections:
            return ConnectionSettingsDTO(
                connection_id=None,
                status=None,
                admin_email=None,
                workspace_domain=None,
                last_sync_completed_at=None,
                last_sync_status=None,
                can_sync=False,
                is_syncing=False,
            )

        connection = connections[0]
        is_syncing = (
            connection.last_sync_started_at is not None
            and connection.last_sync_completed_at is None
        )
        can_sync = connection.status == "active" and not is_syncing

        return ConnectionSettingsDTO(
            connection_id=connection.id,
            status=connection.status,
            admin_email=connection.admin_email,
            workspace_domain=connection.workspace_domain,
            last_sync_completed_at=connection.last_sync_completed_at,
            last_sync_status=connection.last_sync_status,
            can_sync=can_sync,
            is_syncing=is_syncing,
        )

    async def disconnect_workspace(self, organization_id: int) -> bool:
        connections = await self._connection_repo.find_by_organization(organization_id)
        if not connections:
            return False

        connection = connections[0]
        await self._connection_repo.soft_delete(connection.id)
        logger.info(
            "Workspace disconnected for organization_id=%d connection_id=%d",
            organization_id,
            connection.id,
        )
        return True
