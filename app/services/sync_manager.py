import logging
import traceback
from datetime import datetime, timedelta, timezone

from app.core.settings import settings
from app.dtos.crawl_history_dtos import CreateCrawlHistoryDTO, UpdateCrawlHistoryDTO
from app.integrations.core.credentials import CredentialsManager
from app.integrations.core.types import AuthContext
from app.integrations.providers.google_workspace.provider import (
    GOOGLE_WORKSPACE_PROVIDER_SLUG,
)
from app.models.crawl_history import CrawlStatus, CrawlType
from app.repositories.crawl_history_repo import CrawlHistoryRepository
from app.repositories.identity_provider_connection_repository import (
    IdentityProviderConnectionRepository,
)
from app.repositories.identity_provider_repository import IdentityProviderRepository
from app.integrations.providers.factory import get_provider_by_slug
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.services.directory_service import DirectoryService
from app.services.snapshot_service import SnapshotService
from app.services.stream_service import StreamService

logger = logging.getLogger(__name__)


class SyncManager:
    def __init__(
        self,
        connection_repo: IdentityProviderConnectionRepository,
        identity_provider_repo: IdentityProviderRepository,
        auth_config_repo: ProductAuthConfigRepository,
        crawl_history_repo: CrawlHistoryRepository,
        credentials_manager: CredentialsManager,
        directory_service: DirectoryService,
        snapshot_service: SnapshotService,
        stream_service: StreamService,
    ):
        self._connection_repo = connection_repo
        self._identity_provider_repo = identity_provider_repo
        self._auth_config_repo = auth_config_repo
        self._crawl_repo = crawl_history_repo
        self._credentials_manager = credentials_manager
        self._directory_service = directory_service
        self._snapshot_service = snapshot_service
        self._stream_service = stream_service

    async def run_full_sync(self, connection_id: int):
        """
        Runs the full pipeline.
        Ideally this separates Users, Groups, and Tokens into different jobs.
        For now, we focus on the APP RISK part (Snapshot + Stream).
        """
        await self.run_users_sync(connection_id)
        await self.run_groups_sync(connection_id)
        await self.run_snapshot_sync(connection_id)
        await self.run_stream_sync(connection_id)

    async def run_users_sync(self, connection_id: int):
        await self._run_job(connection_id, CrawlType.USERS, self._users_job)

    async def run_groups_sync(self, connection_id: int):
        await self._run_job(connection_id, CrawlType.GROUPS, self._groups_job)


    async def run_snapshot_sync(self, connection_id: int):
        await self._run_job(connection_id, CrawlType.TOKENS, self._snapshot_job)

    async def run_stream_sync(self, connection_id: int):
        await self._run_job(connection_id, CrawlType.EVENTS, self._stream_job)

    async def _run_job(self, connection_id: int, type: CrawlType, job_func):
        connection = await self._connection_repo.find_by_id(connection_id)
        if not connection:
            logger.error(f"Connection {connection_id} not found.")
            return

        # Create Crawl Record
        crawl = await self._crawl_repo.create(
            CreateCrawlHistoryDTO(
                organization_id=connection.organization_id,
                connection_id=connection.id,
                crawl_type=type,
                status=CrawlStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )

        try:
            # Prepare Context
            auth_context = await self._get_auth_context(connection)
            
            # Execute Logic
            stats = await job_func(connection, auth_context)
            
            # Success
            await self._crawl_repo.update(
                crawl.id,
                UpdateCrawlHistoryDTO(
                    status=CrawlStatus.SUCCESS,
                    finished_at=datetime.now(timezone.utc),
                    stats_json=stats,
                ),
            )
        
        except Exception as e:
            logger.error(f"Sync failed for {connection_id}: {e}")
            logger.error(traceback.format_exc())
            await self._crawl_repo.update(
                crawl.id,
                UpdateCrawlHistoryDTO(
                    status=CrawlStatus.ERROR,
                    finished_at=datetime.now(timezone.utc),
                    error_message=str(e),
                    raw_debug_json={"traceback": traceback.format_exc()},
                ),
            )

    async def _users_job(self, connection, auth_context) -> dict:
        count = await self._directory_service.sync_users_for_connection(
            connection, auth_context
        )
        return {"processed_users": count}

    async def _groups_job(self, connection, auth_context) -> dict:
        count = await self._directory_service.sync_groups_for_connection(
            connection, auth_context
        )
        return {"processed_groups": count}

    async def _snapshot_job(self, connection, auth_context) -> dict:
        count = await self._snapshot_service.sync_tokens_for_connection(connection, auth_context)
        return {"processed_tokens": count}

    async def _stream_job(self, connection, auth_context) -> dict:
        # Determine start_time (cursor)
        last_sync = await self._crawl_repo.find_last_successful_crawl(
            connection.id, CrawlType.EVENTS
        )
        
        start_time = None
        logger.info(f"Last sync for connection {connection.id} was {last_sync}")
        if last_sync and last_sync.finished_at:
             # Add buffer or use exact timestamp? Typically exact or slightly overlapping is safer.
             # Using exact finished_at of last sync as start time, or if provider supports state, use that.
             # For Google Workspace, startTime is RFC3339.
             start_time = last_sync.finished_at.isoformat()
        else:
             start_time = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat() # Default lookback
                
        count = await self._stream_service.sync_events_for_connection(connection, auth_context, start_time)
        return {"processed_events": count}

    async def _get_auth_context(self, connection) -> AuthContext:
        auth_config = await self._auth_config_repo.find_by_identity_provider_id(connection.identity_provider_id)
        if not auth_config:
            raise Exception("Auth Config not found")
            
        identity_provider = await self._identity_provider_repo.find_by_id(connection.identity_provider_id)
        if not identity_provider:
             raise Exception(f"Identity Provider {connection.identity_provider_id} not found")
             
        provider = get_provider_by_slug(identity_provider.slug)
        if not provider:
             raise Exception(f"Provider implementation not found for slug: {identity_provider.slug}")
             
        self._credentials_manager.set_provider(provider)

        return await self._credentials_manager.get_valid_credentials(
            connection.id, auth_config.client_id, auth_config.client_secret
        )
