import logging
from datetime import datetime, timezone
from typing import Any

from app.dtos.app_grant_dtos import CreateAppGrantDTO
from app.dtos.oauth_app_dtos import CreateOAuthAppDTO
from app.dtos.oauth_event_dtos import CreateOAuthEventDTO
from app.integrations.core.types import AuthContext, UnifiedTokenEvent
from app.integrations.providers.google_workspace.provider import (
    google_workspace_provider,
)
from app.models.identity_provider_connection import IdentityProviderConnection
from app.repositories.app_grant_repo import AppGrantRepository
from app.repositories.oauth_app_repo import OAuthAppRepository
from app.repositories.oauth_event_repo import OAuthEventRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository

logger = logging.getLogger(__name__)


class StreamService:
    def __init__(
        self,
        user_repository: WorkspaceUserRepository,
        app_repo: OAuthAppRepository,
        grant_repo: AppGrantRepository,
        event_repo: OAuthEventRepository,
    ):
        self._user_repo = user_repository
        self._app_repo = app_repo
        self._grant_repo = grant_repo
        self._event_repo = event_repo

    async def sync_events_for_connection(
        self, 
        connection: IdentityProviderConnection, 
        auth_context: AuthContext,
        start_time: str | None = None
    ) -> int:
        """
        Phase 2: Stream
        Polls activity logs for Authorize, Revoke, and Activity events.
        """
        logger.info(f"Starting Stream Sync (Events) for connection {connection.id} from {start_time}")
        provider = google_workspace_provider
        total_events = 0

        async for events in provider.fetch_token_events(auth_context, start_time):
            for event in events:
                await self._process_event(connection, event)
                total_events += 1
        
        return total_events

    async def _process_event(
        self,
        connection: IdentityProviderConnection,
        event: UnifiedTokenEvent,
    ):
        # 1. Resolve User
        # Note: Event provides email, we need to find internal ID.
        user = await self._user_repo.find_by_email(connection.organization_id, event.user_email)
        if not user:
            logger.warning(f"Skipping event for unknown user: {event.user_email}")
            return

        # 2. Ensure App exists
        app_dto = CreateOAuthAppDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            client_id=event.client_id,
            name=event.app_name or "Unknown App",
            is_system_app=False, # We can't determine this easily from event alone usually, unless we check allowlist
            scopes_summary=event.scopes,
            raw_data=event.raw_data,
        )
        app = await self._app_repo.upsert(app_dto)

        # 3. Log Event (Immutable Timeline)
        # Check for duplicates before creating
        event_time = event.event_time or datetime.now(timezone.utc)
        
        exists = await self._event_repo.exists(
            organization_id=connection.organization_id,
            user_id=user.id,
            app_id=app.id,
            event_type=event.event_type,
            event_time=event_time
        )

        if not exists:
            event_dto = CreateOAuthEventDTO(
                organization_id=connection.organization_id,
                connection_id=connection.id,
                user_id=user.id,
                app_id=app.id,
                event_type=event.event_type,
                event_time=event_time,
                raw_data=event.raw_data,
            )
            await self._event_repo.create(event_dto)
        else:
            logger.info(f"Skipping duplicate event: {event.event_type} for user {user.id} app {app.id} at {event_time}")

        # 4. Update Current State (AppGrant)
        # "Hybrid Sync": Events also update the 'now' state.
        status = "active"
        revoked_at = None
        
        if event.event_type == "revoke":
            status = "revoked"
            revoked_at = event.event_time
        
        granted_at = None
        if event.event_type == "authorize":
            granted_at = event.event_time

        grant_dto = CreateAppGrantDTO(
            organization_id=connection.organization_id,
            connection_id=connection.id,
            user_id=user.id,
            app_id=app.id,
            status=status,
            scopes=event.scopes,
            granted_at=granted_at,
            last_accessed_at=event.event_time, # Activity or Auth implies access
            revoked_at=revoked_at,
            raw_data=event.raw_data,
        )
        await self._grant_repo.upsert(grant_dto)
