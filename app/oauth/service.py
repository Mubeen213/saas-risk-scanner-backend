import secrets
from dataclasses import dataclass
from typing import Any

import asyncpg

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.oauth.base import OAuthProvider
from app.oauth.registry import oauth_provider_registry
from app.oauth.types import OAuthConfig, OAuthTokens, OAuthUserInfo
from app.repositories.product_auth_config_repository import (
    product_auth_config_repository,
)
from app.repositories.provider_repository import provider_repository


@dataclass
class OAuthResult:
    success: bool
    data: Any = None
    error_code: AuthErrorCode | None = None

    @property
    def error_message(self) -> str | None:
        if self.error_code:
            return AUTH_ERROR_MESSAGES.get(self.error_code)
        return None


class OAuthService:

    def __init__(self) -> None:
        self._state_store: dict[str, dict[str, Any]] = {}

    async def get_provider_config(
        self, conn: asyncpg.Connection, provider_slug: str
    ) -> tuple[OAuthProvider, OAuthConfig] | None:
        provider = await provider_repository.find_by_slug(conn, provider_slug)
        if provider is None:
            return None

        auth_config = (
            await product_auth_config_repository.find_platform_config_by_provider_slug(
                conn, provider_slug
            )
        )
        if auth_config is None:
            return None

        oauth_provider = oauth_provider_registry.get(provider_slug)
        if oauth_provider is None:
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
        state = secrets.token_urlsafe(32)
        self._state_store[state] = {
            "provider_slug": provider.provider_slug,
            "frontend_redirect_uri": frontend_redirect_uri,
        }
        return provider.build_authorization_url(config, state)

    def validate_and_consume_state(self, state: str) -> dict[str, Any] | None:
        return self._state_store.pop(state, None)

    async def exchange_code_for_tokens(
        self, provider: OAuthProvider, config: OAuthConfig, code: str
    ) -> OAuthResult:
        tokens = await provider.exchange_code(config, code)
        if tokens is None:
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_TOKEN_EXCHANGE_FAILED,
            )
        return OAuthResult(success=True, data=tokens)

    async def fetch_user_info(
        self, provider: OAuthProvider, config: OAuthConfig, access_token: str
    ) -> OAuthResult:
        user_info = await provider.fetch_user_info(config, access_token)
        if user_info is None:
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_USER_INFO_FAILED,
            )
        return OAuthResult(success=True, data=user_info)


oauth_service = OAuthService()
