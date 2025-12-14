import logging
from datetime import datetime, timezone
from typing import Any

from app.dtos.app_grant_dtos import CreateAppGrantDTO
from app.dtos.oauth_app_dtos import CreateOAuthAppDTO
from app.integrations.core.types import AuthContext, UnifiedToken
from app.integrations.providers.google_workspace.provider import (
    GOOGLE_WORKSPACE_PROVIDER_SLUG,
    google_workspace_provider,
)
from app.models.identity_provider_connection import IdentityProviderConnection
from app.repositories.app_grant_repo import AppGrantRepository
from app.repositories.oauth_app_repo import OAuthAppRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository

logger = logging.getLogger(__name__)


class SnapshotService:
    def __init__(
        self,
        user_repository: WorkspaceUserRepository,
        app_repo: OAuthAppRepository,
        grant_repo: AppGrantRepository,
    ):
        self._user_repo = user_repository
        self._app_repo = app_repo
        self._grant_repo = grant_repo

    async def sync_tokens_for_connection(
        self, connection: IdentityProviderConnection, auth_context: AuthContext
    ) -> int:
        """
        Phase 1: Snapshot
        Iterates all users in the connection and fetches their current tokens.
        """
        logger.info(f"Starting Snapshot Sync (Tokens) for connection {connection.id}")
        provider = google_workspace_provider  # In real DI, we might select based on connection provider
        
        # 1. Get all users
        # Note: In a real large-scale system, we should iterate via cursor, 
        # but for now we fetch all active users to snapshot them.
        users = await self._user_repo.find_all_active_by_connection(connection.id)
        total_tokens = 0

        for user in users:
            async for tokens in provider.fetch_user_tokens(
                auth_context, user.provider_user_id
            ):
                for token in tokens:
                    logger.info(f"Processing token for user {user.id}: {token.client_id} - {token.app_name}")
                    await self._process_token(connection, user.id, token)
                    total_tokens += 1
        
        logger.info(f"Snapshot Sync completed. Processed {total_tokens} grants.")
        return total_tokens

    async def _process_token(
        self,
        connection: IdentityProviderConnection,
        user_id: int,
        token: UnifiedToken,
    ):
        # 1. Ensure App exists
        app_dto = CreateOAuthAppDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            client_id=token.client_id,
            name=token.app_name,
            is_system_app=token.is_system_app,
            scopes_summary=token.scopes,
            raw_data=token.raw_data,
        )
        app = await self._app_repo.upsert(app_dto)

        # 2. Upsert Grant (Active)
        # If it was revoked, this "Snapshot" proves it's active again (User re-authorized)
        grant_dto = CreateAppGrantDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            user_id=user_id,
            app_id=app.id,
            status="active",
            scopes=token.scopes,
            last_accessed_at=datetime.now(timezone.utc), # We verify it exists now
            raw_data=token.raw_data,
        )
        await self._grant_repo.upsert(grant_dto)
