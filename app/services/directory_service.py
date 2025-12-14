
import logging
from datetime import datetime, timezone

from app.dtos.integration.workspace_dtos import (
    CreateWorkspaceGroupDTO,
    CreateWorkspaceUserDTO,
)
from app.integrations.core.types import AuthContext
from app.integrations.providers.google_workspace.provider import (
    google_workspace_provider,
)
from app.models.identity_provider_connection import IdentityProviderConnection
from app.repositories.workspace_group_repository import WorkspaceGroupRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository

logger = logging.getLogger(__name__)


class DirectoryService:
    def __init__(
        self,
        user_repository: WorkspaceUserRepository,
        group_repository: WorkspaceGroupRepository,
    ):
        self._user_repo = user_repository
        self._group_repo = group_repository

    async def sync_users_for_connection(
        self, connection: IdentityProviderConnection, auth_context: AuthContext
    ) -> int:
        """
        Syncs users from the provider to the local database.
        """
        logger.info(f"Starting User Sync for connection {connection.id}")
        provider = google_workspace_provider
        total_users = 0

        async for users in provider.fetch_users(auth_context):
            dtos = []
            for user in users:
                dtos.append(
                    CreateWorkspaceUserDTO(
                        organization_id=connection.organization_id,
                        connection_id=connection.id,
                        provider_user_id=user.provider_id,
                        email=user.email,
                        full_name=user.full_name,
                        given_name=user.given_name,
                        family_name=user.family_name,
                        is_admin=user.is_admin,
                        is_delegated_admin=user.is_delegated_admin,
                        status="suspended" if user.raw_data.get("suspended") else "active",
                        org_unit_path=user.org_unit_path,
                        avatar_url=user.avatar_url,
                        raw_data=user.raw_data,
                    )
                )
            
            if dtos:
                count = await self._user_repo.bulk_upsert(dtos)
                total_users += count
                logger.debug(f"Upserted batch of {count} users")

        logger.info(f"User Sync completed. Processed {total_users} users.")
        return total_users

    async def sync_groups_for_connection(
        self, connection: IdentityProviderConnection, auth_context: AuthContext
    ) -> int:
        """
        Syncs groups from the provider to the local database.
        """
        logger.info(f"Starting Group Sync for connection {connection.id}")
        provider = google_workspace_provider
        total_groups = 0

        async for groups in provider.fetch_groups(auth_context):
            dtos = []
            for group in groups:
                dtos.append(
                    CreateWorkspaceGroupDTO(
                        organization_id=connection.organization_id,
                        connection_id=connection.id,
                        provider_group_id=group.provider_id,
                        email=group.email,
                        name=group.name,
                        description=group.description,
                        raw_data=group.raw_data,
                    )
                )

            if dtos:
                count = await self._group_repo.bulk_upsert(dtos)
                total_groups += count
                logger.debug(f"Upserted batch of {count} groups")
        
        logger.info(f"Group Sync completed. Processed {total_groups} groups.")
        return total_groups
