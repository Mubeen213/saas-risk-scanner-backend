import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from cryptography.fernet import Fernet

from app.constants.enums import ConnectionStatus
from app.dtos.integration.connection_dtos import (
    CreateIdentityProviderConnectionDTO,
    UpdateIdentityProviderConnectionDTO,
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
from app.models.identity_provider_connection import IdentityProviderConnection
from app.models.product_auth_config import ProductAuthConfig
from app.oauth.types import OAuthTokens
from app.repositories.identity_provider_connection_repository import (
    IdentityProviderConnectionRepository,
)
from app.repositories.identity_provider_repository import IdentityProviderRepository
from app.repositories.product_auth_config_repository import (
    ProductAuthConfigRepository,
)

logger = logging.getLogger(__name__)


class IntegrationService:
    def __init__(
        self,
        identity_provider_repository: IdentityProviderRepository,
        product_auth_config_repository: ProductAuthConfigRepository,
        connection_repository: IdentityProviderConnectionRepository,
        encryption_key: str,
    ):
        self._identity_provider_repo = identity_provider_repository
        self._auth_config_repo = product_auth_config_repository
        self._connection_repo = connection_repository
        self._fernet = Fernet(encryption_key.encode())

    async def get_connect_url(
        self,
        identity_provider_slug: str,
        state: str,
        redirect_uri: str,
    ) -> str:
        logger.info(
            f"Building connect URL for identity provider: {identity_provider_slug}"
        )
        identity_provider = await self._identity_provider_repo.find_by_slug(
            identity_provider_slug
        )
        if not identity_provider:
            logger.warning(f"Identity provider not found: {identity_provider_slug}")
            raise ProviderNotFoundError(identity_provider_slug)

        auth_config = await self._auth_config_repo.find_by_identity_provider_id(
            identity_provider.id
        )
        if not auth_config:
            logger.warning(
                f"Auth config not found for identity provider: {identity_provider_slug}"
            )
            raise ProviderNotFoundError(identity_provider_slug)

        scopes = self._get_admin_scopes(identity_provider_slug)

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
            f"Connect URL built successfully for identity provider: {identity_provider_slug} and params: {params}"
        )
        return f"{auth_config.authorization_url}?{urlencode(params)}"

    async def handle_oauth_callback(
        self,
        identity_provider_slug: str,
        code: str,
        organization_id: int,
        user_id: int,
        user_email: str,
        redirect_uri: str,
    ) -> IdentityProviderConnection:
        logger.info(
            "Handling OAuth callback for identity provider: %s, org: %d",
            identity_provider_slug,
            organization_id,
        )
        identity_provider = await self._identity_provider_repo.find_by_slug(
            identity_provider_slug
        )
        if not identity_provider:
            logger.warning("Identity provider not found: %s", identity_provider_slug)
            raise ProviderNotFoundError(identity_provider_slug)

        existing = await self._connection_repo.find_by_org_and_identity_provider(
            organization_id, identity_provider.id
        )
        if existing and existing.status == ConnectionStatus.ACTIVE.value:
            logger.warning(
                "Active connection already exists for org: %d, identity provider: %s",
                organization_id,
                identity_provider_slug,
            )
            raise ConnectionAlreadyExistsError(organization_id, identity_provider_slug)

        auth_config = await self._auth_config_repo.find_by_identity_provider_id(
            identity_provider.id
        )
        if not auth_config:
            logger.warning(
                "Auth config not found for identity provider: %s",
                identity_provider_slug,
            )
            raise ProviderNotFoundError(identity_provider_slug)

        tokens = await self._exchange_code_for_tokens(
            auth_config, code, identity_provider_slug, redirect_uri
        )

        if existing:
            logger.info("Updating existing connection: %d", existing.id)
            return await self._update_existing_connection(
                existing.id, tokens, user_email
            )

        logger.info(
            "Creating new connection for org: %d, identity provider: %s",
            organization_id,
            identity_provider_slug,
        )
        return await self._create_new_connection(
            organization_id, identity_provider.id, user_id, tokens, user_email
        )

    async def find_connection_by_id(
        self, connection_id: int
    ) -> IdentityProviderConnection:
        logger.debug("Finding connection by ID: %d", connection_id)
        connection = await self._connection_repo.find_by_id(connection_id)
        if not connection:
            logger.warning("Connection not found: %d", connection_id)
            raise ConnectionNotFoundError(connection_id)
        return connection

    async def get_organization_connections(
        self, organization_id: int
    ) -> list[IdentityProviderConnection]:
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

    def _get_admin_scopes(self, identity_provider_slug: str) -> list[str]:
        if identity_provider_slug == GOOGLE_WORKSPACE_PROVIDER_SLUG:
            return GOOGLE_WORKSPACE_ADMIN_SCOPES
        return []

    async def _exchange_code_for_tokens(
        self,
        auth_config: ProductAuthConfig,
        code: str,
        identity_provider_slug: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        from app.integrations.providers.google_workspace import (
            google_workspace_provider,
        )

        if identity_provider_slug == GOOGLE_WORKSPACE_PROVIDER_SLUG:
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

        raise ProviderNotFoundError(identity_provider_slug)

    async def _create_new_connection(
        self,
        organization_id: int,
        identity_provider_id: int,
        user_id: int,
        tokens: OAuthTokens,
        user_email: str,
    ) -> IdentityProviderConnection:
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens.expires_in
            )

        dto = CreateIdentityProviderConnectionDTO(
            organization_id=organization_id,
            identity_provider_id=identity_provider_id,
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
    ) -> IdentityProviderConnection:
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens.expires_in
            )

        dto = UpdateIdentityProviderConnectionDTO(
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
