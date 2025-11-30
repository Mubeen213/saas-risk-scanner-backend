import logging
from dataclasses import dataclass
from typing import Any

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.oauth.base import OAuthProvider
from app.oauth.registry import oauth_provider_registry
from app.oauth.types import OAuthConfig, OAuthTokens, OAuthUserInfo
from app.repositories.identity_provider_repository import IdentityProviderRepository
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.utils.oauth_state import create_signed_state, verify_signed_state

logger = logging.getLogger(__name__)


@dataclass
class OAuthResult:
    success: bool
    data: OAuthTokens | OAuthUserInfo | None = None
    error_code: AuthErrorCode | None = None

    @property
    def error_message(self) -> str | None:
        if self.error_code:
            return AUTH_ERROR_MESSAGES.get(self.error_code)
        return None


class OAuthService:

    def __init__(
        self,
        identity_provider_repository: IdentityProviderRepository,
        product_auth_config_repository: ProductAuthConfigRepository,
    ):
        self._identity_provider_repository = identity_provider_repository
        self._product_auth_config_repository = product_auth_config_repository

    async def get_provider_config(
        self, identity_provider_slug: str
    ) -> tuple[OAuthProvider, OAuthConfig] | None:
        logger.debug(f"Fetching provider config for: {identity_provider_slug}")
        identity_provider = await self._identity_provider_repository.find_by_slug(
            identity_provider_slug
        )
        if identity_provider is None:
            logger.warning(f"Identity provider not found: {identity_provider_slug}")
            return None

        auth_config = await self._product_auth_config_repository.find_platform_config_by_identity_provider_slug(
            identity_provider_slug
        )
        if auth_config is None:
            logger.warning(
                f"Auth config not found for identity provider: {identity_provider_slug}"
            )
            return None

        oauth_provider = oauth_provider_registry.get(identity_provider_slug)
        if oauth_provider is None:
            logger.warning(f"OAuth provider not registered: {identity_provider_slug}")
            return None

        config = OAuthConfig(
            client_id=auth_config.client_id,
            client_secret=auth_config.client_secret,
            authorization_url=auth_config.authorization_url,
            token_url=auth_config.token_url,
            userinfo_url=auth_config.userinfo_url,
            revoke_url=auth_config.revoke_url,
            scopes=auth_config.scopes,
            redirect_uri=auth_config.redirect_uri,
            additional_params=auth_config.additional_params,
        )
        return oauth_provider, config

    def generate_authorization_url(
        self,
        provider: OAuthProvider,
        config: OAuthConfig,
        frontend_redirect_uri: str,
    ) -> str:
        state = create_signed_state(provider.provider_slug, frontend_redirect_uri)
        return provider.build_authorization_url(config, state)

    def validate_and_consume_state(self, state: str) -> dict[str, Any] | None:
        return verify_signed_state(state)

    async def exchange_code_for_tokens(
        self, provider: OAuthProvider, config: OAuthConfig, code: str
    ) -> OAuthResult:
        logger.debug(
            f"Exchanging code for tokens with provider: {provider.provider_slug}"
        )
        tokens = await provider.exchange_code(config, code)
        if tokens is None:
            logger.warning(
                f"Token exchange failed for provider: {provider.provider_slug}"
            )
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_TOKEN_EXCHANGE_FAILED,
            )
        logger.info(f"Token exchange successful for provider: {provider.provider_slug}")
        return OAuthResult(success=True, data=tokens)

    async def fetch_user_info(
        self, provider: OAuthProvider, config: OAuthConfig, access_token: str
    ) -> OAuthResult:
        logger.debug(f"Fetching user info from provider: {provider.provider_slug}")
        user_info = await provider.fetch_user_info(config, access_token)
        if user_info is None:
            logger.warning(
                f"Failed to fetch user info from provider: {provider.provider_slug}"
            )
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_USER_INFO_FAILED,
            )
        logger.info(f"User info fetched successfully for: {user_info.email}")
        return OAuthResult(success=True, data=user_info)
