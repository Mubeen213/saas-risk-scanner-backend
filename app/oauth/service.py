import logging
from dataclasses import dataclass
from typing import Any

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.oauth.base import OAuthProvider
from app.oauth.registry import oauth_provider_registry
from app.oauth.types import OAuthConfig, OAuthTokens, OAuthUserInfo
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.repositories.provider_repository import ProviderRepository
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
        provider_repository: ProviderRepository,
        product_auth_config_repository: ProductAuthConfigRepository,
    ):
        self._provider_repository = provider_repository
        self._product_auth_config_repository = product_auth_config_repository

    async def get_provider_config(
        self, provider_slug: str
    ) -> tuple[OAuthProvider, OAuthConfig] | None:
        logger.debug("Fetching provider config for: %s", provider_slug)
        provider = await self._provider_repository.find_by_slug(provider_slug)
        if provider is None:
            logger.warning("Provider not found: %s", provider_slug)
            return None

        auth_config = await self._product_auth_config_repository.find_platform_config_by_provider_slug(
            provider_slug
        )
        if auth_config is None:
            logger.warning("Auth config not found for provider: %s", provider_slug)
            return None

        oauth_provider = oauth_provider_registry.get(provider_slug)
        if oauth_provider is None:
            logger.warning("OAuth provider not registered: %s", provider_slug)
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
            "Exchanging code for tokens with provider: %s", provider.provider_slug
        )
        tokens = await provider.exchange_code(config, code)
        if tokens is None:
            logger.warning(
                "Token exchange failed for provider: %s", provider.provider_slug
            )
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_TOKEN_EXCHANGE_FAILED,
            )
        logger.info(
            "Token exchange successful for provider: %s", provider.provider_slug
        )
        return OAuthResult(success=True, data=tokens)

    async def fetch_user_info(
        self, provider: OAuthProvider, config: OAuthConfig, access_token: str
    ) -> OAuthResult:
        logger.debug("Fetching user info from provider: %s", provider.provider_slug)
        user_info = await provider.fetch_user_info(config, access_token)
        if user_info is None:
            logger.warning(
                "Failed to fetch user info from provider: %s", provider.provider_slug
            )
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_USER_INFO_FAILED,
            )
        logger.info("User info fetched successfully for: %s", user_info.email)
        return OAuthResult(success=True, data=user_info)
