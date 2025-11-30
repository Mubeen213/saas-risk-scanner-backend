import logging
from datetime import datetime, timezone

from app.constants.enums import (
    AuthorizationStatus,
    WorkspaceUserStatus,
)
from app.dtos.integration.discovery_dtos import (
    CreateAppAuthorizationDTO,
    CreateDiscoveredAppDTO,
)
from app.dtos.integration.workspace_dtos import (
    CreateGroupMembershipDTO,
    CreateWorkspaceGroupDTO,
    CreateWorkspaceUserDTO,
)
from app.integrations.core.credentials import CredentialsManager
from app.integrations.core.exceptions import ConnectionNotFoundError, SyncError
from app.integrations.core.types import (
    AuthContext,
    SyncStatus,
    UnifiedGroup,
    UnifiedGroupMembership,
    UnifiedTokenEvent,
    UnifiedUser,
)
from app.integrations.providers.google_workspace import (
    GOOGLE_WORKSPACE_PROVIDER_SLUG,
    google_workspace_provider,
)
from app.models.identity_provider import IdentityProvider
from app.models.identity_provider_connection import IdentityProviderConnection
from app.repositories.app_authorization_repository import AppAuthorizationRepository
from app.repositories.discovered_app_repository import DiscoveredAppRepository
from app.repositories.identity_provider_connection_repository import (
    IdentityProviderConnectionRepository,
)
from app.repositories.identity_provider_repository import IdentityProviderRepository
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.repositories.workspace_group_repository import WorkspaceGroupRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository

logger = logging.getLogger(__name__)


class WorkspaceSyncService:
    def __init__(
        self,
        connection_repository: IdentityProviderConnectionRepository,
        identity_provider_repository: IdentityProviderRepository,
        auth_config_repository: ProductAuthConfigRepository,
        workspace_user_repository: WorkspaceUserRepository,
        workspace_group_repository: WorkspaceGroupRepository,
        discovered_app_repository: DiscoveredAppRepository,
        app_authorization_repository: AppAuthorizationRepository,
        credentials_manager: CredentialsManager,
    ):
        self._connection_repo = connection_repository
        self._identity_provider_repo = identity_provider_repository
        self._auth_config_repo = auth_config_repository
        self._user_repo = workspace_user_repository
        self._group_repo = workspace_group_repository
        self._app_repo = discovered_app_repository
        self._auth_repo = app_authorization_repository
        self._credentials_manager = credentials_manager

    async def sync_workspace(self, connection_id: int) -> SyncStatus:
        logger.info(f"Starting workspace sync for connection: {connection_id}")
        connection = await self._connection_repo.find_by_id(connection_id)
        if not connection:
            logger.warning(f"Connection not found for sync: {connection_id}")
            raise ConnectionNotFoundError(connection_id)

        logger.debug(
            f"Connection found: org_id={connection.organization_id}, identity_provider_id={connection.identity_provider_id}"
        )
        await self._connection_repo.mark_sync_started(connection_id)

        try:
            identity_provider: IdentityProvider | None = (
                await self._identity_provider_repo.find_by_id(
                    connection.identity_provider_id
                )
            )
            if not identity_provider:
                logger.error(
                    f"Identity provider not found for id: {connection.identity_provider_id}"
                )
                raise SyncError("init", "Identity provider not found")

            logger.debug(f"Identity provider found: slug={identity_provider.slug}")

            auth_config = await self._auth_config_repo.find_by_identity_provider_id(
                identity_provider.id
            )
            if not auth_config:
                logger.error(
                    f"Auth config not found for identity provider: {identity_provider.id}"
                )
                raise SyncError("init", "Auth config not found")

            logger.debug(
                f"Auth config loaded for identity provider: {identity_provider.slug} and authConfig: {auth_config}"
            )

            auth_context = await self._credentials_manager.get_valid_credentials(
                connection_id, auth_config.client_id, auth_config.client_secret
            )
            logger.debug(f"Credentials obtained for connection: {connection_id}")

            workspace_provider = self._get_workspace_provider(identity_provider.slug)
            self._credentials_manager.set_provider(workspace_provider)

            logger.debug(f"Starting user sync for connection: {connection_id}")
            await self._sync_users(connection, auth_context)

            logger.debug(f"Starting group sync for connection: {connection_id}")
            await self._sync_groups(connection, auth_context)

            logger.debug(
                f"Starting group membership sync for connection: {connection_id}"
            )
            await self._sync_group_memberships(connection, auth_context)

            logger.debug(f"Starting token events sync for connection: {connection_id}")
            await self._sync_token_events(connection, auth_context)

            await self._connection_repo.update_sync_status(
                connection_id, SyncStatus.COMPLETED.value
            )

            logger.info(f"Sync completed for connection {connection_id}")
            return SyncStatus.COMPLETED

        except Exception as e:
            logger.error(f"Sync failed for connection {connection_id}: {e}")
            await self._connection_repo.update_sync_status(
                connection_id, SyncStatus.FAILED.value, str(e)
            )
            raise SyncError("sync", str(e)) from e

    async def _sync_users(
        self,
        connection: IdentityProviderConnection,
        auth_context: AuthContext,
    ) -> int:
        provider = self._get_workspace_provider(GOOGLE_WORKSPACE_PROVIDER_SLUG)
        total_synced = 0

        async for users_batch in provider.fetch_users(auth_context):
            for user in users_batch:
                await self._upsert_workspace_user(connection, user)
                total_synced += 1

        logger.info("Synced %d users for connection %d", total_synced, connection.id)
        return total_synced

    async def _sync_groups(
        self,
        connection: IdentityProviderConnection,
        auth_context: AuthContext,
    ) -> int:
        provider = self._get_workspace_provider(GOOGLE_WORKSPACE_PROVIDER_SLUG)
        total_synced = 0

        async for groups_batch in provider.fetch_groups(auth_context):
            for group in groups_batch:
                await self._upsert_workspace_group(connection, group)
                total_synced += 1

        logger.info("Synced %d groups for connection %d", total_synced, connection.id)
        return total_synced

    async def _sync_group_memberships(
        self,
        connection: IdentityProviderConnection,
        auth_context: AuthContext,
    ) -> int:
        provider = self._get_workspace_provider(GOOGLE_WORKSPACE_PROVIDER_SLUG)
        groups = await self._group_repo.find_by_connection(connection.id)
        total_synced = 0

        for group in groups:
            await self._group_repo.delete_memberships_for_group(group.id)

            async for memberships_batch in provider.fetch_group_members(
                auth_context, group.provider_group_id
            ):
                for membership in memberships_batch:
                    await self._upsert_group_membership(
                        connection.organization_id, group.id, membership
                    )
                    total_synced += 1

        logger.info(
            "Synced %d memberships for connection %d", total_synced, connection.id
        )
        return total_synced

    async def _sync_token_events(
        self,
        connection: IdentityProviderConnection,
        auth_context: AuthContext,
    ) -> int:
        provider = self._get_workspace_provider(GOOGLE_WORKSPACE_PROVIDER_SLUG)
        total_synced = 0

        async for events_batch in provider.fetch_token_events(auth_context):
            for event in events_batch:
                await self._process_token_event(connection, event)
                total_synced += 1

        logger.info(
            f"Synced {total_synced} token events for connection {connection.id}"
        )
        return total_synced

    async def _upsert_workspace_user(
        self,
        connection: IdentityProviderConnection,
        user: UnifiedUser,
    ) -> None:
        dto = CreateWorkspaceUserDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            provider_user_id=user.provider_id,
            email=user.email,
            full_name=user.full_name,
            given_name=user.given_name,
            family_name=user.family_name,
            is_admin=user.is_admin,
            is_delegated_admin=user.is_delegated_admin,
            status=WorkspaceUserStatus.ACTIVE.value,
            org_unit_path=user.org_unit_path,
            avatar_url=user.avatar_url,
            raw_data=user.raw_data,
        )
        logger.debug(
            f"Upserting user: {user.email} with provider ID: {user.provider_id}"
        )
        await self._user_repo.upsert(dto)

    async def _upsert_workspace_group(
        self,
        connection: IdentityProviderConnection,
        group: UnifiedGroup,
    ) -> None:
        dto = CreateWorkspaceGroupDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            provider_group_id=group.provider_id,
            email=group.email,
            name=group.name,
            description=group.description,
            direct_members_count=group.direct_members_count,
            raw_data=group.raw_data,
        )
        logger.debug(
            f"Upserting group: {group.email} with provider ID: {group.provider_id}"
        )
        await self._group_repo.upsert(dto)

    async def _upsert_group_membership(
        self,
        organization_id: int,
        group_id: int,
        membership: UnifiedGroupMembership,
    ) -> None:
        user = await self._user_repo.find_by_provider_user_id(
            organization_id, membership.user_provider_id
        )
        if not user:
            logger.debug(
                f"User not found for group membership: {membership.user_provider_id}"
            )
            return
        logger.debug(
            f"Upserting group membership: user_id={user.id}, group_id={group_id}, role={membership.role}"
        )
        dto = CreateGroupMembershipDTO(
            workspace_user_id=user.id,
            workspace_group_id=group_id,
            role=membership.role,
        )
        await self._group_repo.upsert_membership(dto)

    async def _process_token_event(
        self,
        connection: IdentityProviderConnection,
        event: UnifiedTokenEvent,
    ) -> None:
        user = await self._user_repo.find_by_email(
            connection.organization_id, event.user_email
        )
        if not user:
            logger.debug(f"User not found for token event: {event.user_email}")
            return

        app = await self._upsert_discovered_app(connection, event)

        if event.event_type == "authorize":
            await self._upsert_authorization(app.id, user.id, event)
        elif event.event_type == "revoke":
            existing_auth = await self._auth_repo.find_by_app_and_user(app.id, user.id)
            if existing_auth:
                await self._auth_repo.mark_revoked(existing_auth.id, event.event_time)

    async def _upsert_discovered_app(
        self,
        connection: IdentityProviderConnection,
        event: UnifiedTokenEvent,
    ):
        event_time = event.event_time or datetime.now(timezone.utc)
        logger.debug(
            f"Upserting discovered app: {event.app_name} for connection: {connection.id}"
        )
        dto = CreateDiscoveredAppDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            client_id=event.client_id,
            display_name=event.app_name,
            client_type=event.client_type,
            status="active",
            first_seen_at=event_time,
            last_seen_at=event_time,
            all_scopes=event.scopes,
            raw_data=event.raw_data,
        )
        return await self._app_repo.upsert(dto)

    async def _upsert_authorization(
        self,
        app_id: int,
        user_id: int,
        event: UnifiedTokenEvent,
    ) -> None:
        event_time = event.event_time or datetime.now(timezone.utc)
        logger.debug(
            f"Upserting app authorization for app_id: {app_id}, user_id: {user_id}"
        )
        dto = CreateAppAuthorizationDTO(
            discovered_app_id=app_id,
            workspace_user_id=user_id,
            scopes=event.scopes,
            status=AuthorizationStatus.ACTIVE.value,
            authorized_at=event_time,
            raw_data=event.raw_data,
        )
        await self._auth_repo.upsert(dto)

    def _get_workspace_provider(self, provider_slug: str):
        if provider_slug == GOOGLE_WORKSPACE_PROVIDER_SLUG:
            return google_workspace_provider
        raise SyncError("provider", f"Unsupported provider: {provider_slug}")
