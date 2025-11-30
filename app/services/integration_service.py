import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from cryptography.fernet import Fernet

from app.constants.enums import ConnectionStatus
from app.dtos.integration.connection_dtos import (
    CreateOrgProviderConnectionDTO,
    UpdateOrgProviderConnectionDTO,
)
from app.integrations.core.exceptions import (
    ConnectionAlreadyExistsError,
    ConnectionNotFoundError,
    ProviderNotFoundError,
)
from app.integrations.providers.google_workspace.constants import (
    GOOGLE_WORKSPACE_ADMIN_SCOPES,
    GOOGLE_WORKSPACE_PROVIDER_SLUG,
)
from app.models.org_provider_connection import OrgProviderConnection
from app.models.product_auth_config import ProductAuthConfig
from app.oauth.types import OAuthTokens
from app.repositories.org_provider_connection_repository import (
    OrgProviderConnectionRepository,
)
from app.repositories.product_auth_config_repository import (
    ProductAuthConfigRepository,
)
from app.repositories.provider_repository import ProviderRepository

logger = logging.getLogger(__name__)


class IntegrationService:
    def __init__(
        self,
        provider_repository: ProviderRepository,
        product_auth_config_repository: ProductAuthConfigRepository,
        connection_repository: OrgProviderConnectionRepository,
        encryption_key: str,
    ):
        self._provider_repo = provider_repository
        self._auth_config_repo = product_auth_config_repository
        self._connection_repo = connection_repository
        self._fernet = Fernet(encryption_key.encode())

    async def get_connect_url(
        self,
        provider_slug: str,
        state: str,
        redirect_uri: str,
    ) -> str:
        logger.info(f"Building connect URL for provider: {provider_slug}")
        provider = await self._provider_repo.find_by_slug(provider_slug)
        if not provider:
            logger.warning(f"Provider not found: {provider_slug}")
            raise ProviderNotFoundError(provider_slug)

        auth_config = await self._auth_config_repo.find_by_provider_id(provider.id)
        if not auth_config:
            logger.warning(f"Auth config not found for provider: {provider_slug}")
            raise ProviderNotFoundError(provider_slug)

        scopes = self._get_admin_scopes(provider_slug)

        params = {
            "client_id": auth_config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        logger.debug(
            f"Connect URL built successfully for provider: {provider_slug} and params: {params}"
        )
        return f"{auth_config.authorization_url}?{urlencode(params)}"

    async def handle_oauth_callback(
        self,
        provider_slug: str,
        code: str,
        organization_id: int,
        user_id: int,
        user_email: str,
        redirect_uri: str,
    ) -> OrgProviderConnection:
        logger.info(
            "Handling OAuth callback for provider: %s, org: %d",
            provider_slug,
            organization_id,
        )
        provider = await self._provider_repo.find_by_slug(provider_slug)
        if not provider:
            logger.warning("Provider not found: %s", provider_slug)
            raise ProviderNotFoundError(provider_slug)

        existing = await self._connection_repo.find_by_org_and_provider(
            organization_id, provider.id
        )
        if existing and existing.status == ConnectionStatus.ACTIVE.value:
            logger.warning(
                "Active connection already exists for org: %d, provider: %s",
                organization_id,
                provider_slug,
            )
            raise ConnectionAlreadyExistsError(organization_id, provider_slug)

        auth_config = await self._auth_config_repo.find_by_provider_id(provider.id)
        if not auth_config:
            logger.warning("Auth config not found for provider: %s", provider_slug)
            raise ProviderNotFoundError(provider_slug)

        tokens = await self._exchange_code_for_tokens(
            auth_config, code, provider_slug, redirect_uri
        )

        if existing:
            logger.info("Updating existing connection: %d", existing.id)
            return await self._update_existing_connection(
                existing.id, tokens, user_email
            )

        logger.info(
            "Creating new connection for org: %d, provider: %s",
            organization_id,
            provider_slug,
        )
        return await self._create_new_connection(
            organization_id, provider.id, user_id, tokens, user_email
        )

    async def find_connection_by_id(self, connection_id: int) -> OrgProviderConnection:
        logger.debug("Finding connection by ID: %d", connection_id)
        connection = await self._connection_repo.find_by_id(connection_id)
        if not connection:
            logger.warning("Connection not found: %d", connection_id)
            raise ConnectionNotFoundError(connection_id)
        return connection

    async def get_organization_connections(
        self, organization_id: int
    ) -> list[OrgProviderConnection]:
        logger.debug("Fetching connections for organization: %d", organization_id)
        return await self._connection_repo.find_by_organization(organization_id)

    async def disconnect(self, connection_id: int) -> bool:
        logger.info("Disconnecting connection: %d", connection_id)
        connection = await self._connection_repo.find_by_id(connection_id)
        if not connection:
            logger.warning("Connection not found for disconnect: %d", connection_id)
            raise ConnectionNotFoundError(connection_id)

        result = await self._connection_repo.soft_delete(connection_id)
        logger.info("Connection %d disconnected: %s", connection_id, result)
        return result

    def _get_admin_scopes(self, provider_slug: str) -> list[str]:
        if provider_slug == GOOGLE_WORKSPACE_PROVIDER_SLUG:
            return GOOGLE_WORKSPACE_ADMIN_SCOPES
        return []

    async def _exchange_code_for_tokens(
        self,
        auth_config: ProductAuthConfig,
        code: str,
        provider_slug: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        from app.integrations.providers.google_workspace import (
            google_workspace_provider,
        )

        if provider_slug == GOOGLE_WORKSPACE_PROVIDER_SLUG:
            token_response = await google_workspace_provider.exchange_code_for_tokens(
                code=code,
                client_id=auth_config.client_id,
                client_secret=auth_config.client_secret,
                redirect_uri=redirect_uri,
            )
            return OAuthTokens(
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_type=token_response.token_type,
                expires_in=token_response.expires_in,
                scope=token_response.scope,
            )

        raise ProviderNotFoundError(provider_slug)

    async def _create_new_connection(
        self,
        organization_id: int,
        provider_id: int,
        user_id: int,
        tokens: OAuthTokens,
        user_email: str,
    ) -> OrgProviderConnection:
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens.expires_in
            )

        dto = CreateOrgProviderConnectionDTO(
            organization_id=organization_id,
            provider_id=provider_id,
            connected_by_user_id=user_id,
            status=ConnectionStatus.ACTIVE.value,
            access_token_encrypted=self._encrypt(tokens.access_token),
            refresh_token_encrypted=(
                self._encrypt(tokens.refresh_token) if tokens.refresh_token else None
            ),
            token_expires_at=expires_at,
            scopes_granted=tokens.scope.split(" ") if tokens.scope else [],
            admin_email=user_email,
            workspace_domain=user_email.split("@")[1] if "@" in user_email else None,
        )

        return await self._connection_repo.create(dto)

    async def _update_existing_connection(
        self,
        connection_id: int,
        tokens: OAuthTokens,
        user_email: str,
    ) -> OrgProviderConnection:
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens.expires_in
            )

        dto = UpdateOrgProviderConnectionDTO(
            status=ConnectionStatus.ACTIVE.value,
            access_token_encrypted=self._encrypt(tokens.access_token),
            refresh_token_encrypted=(
                self._encrypt(tokens.refresh_token) if tokens.refresh_token else None
            ),
            token_expires_at=expires_at,
            scopes_granted=tokens.scope.split(" ") if tokens.scope else None,
            error_code=None,
            error_message=None,
        )

        return await self._connection_repo.update(connection_id, dto)

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted_value: str) -> str:
        return self._fernet.decrypt(encrypted_value.encode()).decode()
