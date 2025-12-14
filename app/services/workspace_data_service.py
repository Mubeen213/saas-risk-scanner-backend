import logging

from app.dtos.workspace_dtos import (
    ConnectionSettingsDTO,
    GroupWithMembersDTO,
    PaginationParamsDTO,
    UserWithAuthorizationsDTO,
    WorkspaceGroupWithMemberCountDTO,
    WorkspaceStatsDTO,
    WorkspaceUserWithAppCountDTO,
    AppWithAuthorizationsDTO,
)
from app.dtos.oauth_app_dtos import OAuthAppWithStatsDTO
from app.dtos.oauth_event_dtos import OAuthEventResponseDTO
from app.repositories.app_grant_repo import AppGrantRepository
from app.repositories.oauth_app_repo import OAuthAppRepository
from app.repositories.oauth_event_repo import OAuthEventRepository
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
        oauth_app_repo: OAuthAppRepository,
        app_grant_repo: AppGrantRepository,
        oauth_event_repo: OAuthEventRepository,
    ):
        self._connection_repo = connection_repository
        self._user_repo = workspace_user_repository
        self._group_repo = workspace_group_repository
        self._app_repo = oauth_app_repo
        self._grant_repo = app_grant_repo
        self._event_repo = oauth_event_repo

    async def get_workspace_stats(self, organization_id: int) -> WorkspaceStatsDTO:
        total_users = await self._user_repo.count_by_organization(organization_id)
        total_groups = await self._group_repo.count_by_organization(organization_id)
        total_apps = await self._app_repo.count_by_organization(organization_id)
        active_authorizations = await self._grant_repo.count_active_by_organization(
            organization_id
        )

        connections = await self._connection_repo.find_by_organization(organization_id)
        last_sync_at = None
        if connections:
            active_connection = next(
                (c for c in connections if c.status == "active"), None
            )
            if active_connection:
                last_sync_at = None

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
    ) -> tuple[list[OAuthAppWithStatsDTO], int]:
        dtos = await self._app_repo.find_paginated_with_stats(
            organization_id, params.page_size, (params.page - 1) * params.page_size, params.search
        )
        total = await self._app_repo.count_by_organization(organization_id)
        
        return dtos, total

    async def get_app_with_authorizations(
        self, organization_id: int, app_id: int
    ) -> AppWithAuthorizationsDTO | None:
        app = await self._app_repo.find_by_id(app_id)
        if not app or app.organization_id != organization_id:
            return None
            
        authorizations = await self._grant_repo.find_by_app_with_users(organization_id, app_id)
        
        return AppWithAuthorizationsDTO(
            id=app.id,
            name=app.name,
            client_id=app.client_id,
            status="active" if app.is_trusted else "review",
            risk_score=app.risk_score,
            is_system_app=app.is_system_app,
            is_trusted=app.is_trusted,
            all_scopes=app.scopes_summary,
            active_grants_count=len(authorizations), # Approximate count from loaded auths
            last_activity_at=None,
            authorizations=authorizations
        )

    async def get_app_timeline(
        self, organization_id: int, app_id: int, params: PaginationParamsDTO, user_id: int | None = None
    ) -> tuple[list[OAuthEventResponseDTO], int]:
        dtos = await self._event_repo.find_paginated_by_app(
            organization_id, 
            app_id, 
            params.page_size, 
            (params.page - 1) * params.page_size,
            user_id
        )
        total = await self._event_repo.count_by_app(organization_id, app_id, user_id)
        
        return dtos, total

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
        is_syncing = False
        can_sync = connection.status == "active"

        return ConnectionSettingsDTO(
            connection_id=connection.id,
            status=connection.status,
            admin_email=connection.admin_email,
            workspace_domain=connection.workspace_domain,
            last_sync_completed_at=None,
            last_sync_status=None,
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
