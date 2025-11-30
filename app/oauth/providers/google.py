import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from app.oauth.base import OAuthProvider
from app.oauth.types import OAuthConfig, OAuthTokens, OAuthUserInfo

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class GoogleOAuthProvider(OAuthProvider):

    @property
    def provider_slug(self) -> str:
        return "google-workspace"

    def build_authorization_url(self, config: OAuthConfig, state: str) -> str:
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        params.update(config.additional_params)
        return f"{config.authorization_url}?{urlencode(params)}"

    def _sync_exchange_code(self, config: OAuthConfig, code: str) -> OAuthTokens | None:
        """Synchronous token exchange using google-auth-oauthlib."""
        try:
            logger.debug("Exchanging code for tokens with Google OAuth")
            flow = Flow.from_client_config(
                client_config={
                    "web": {
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                        "auth_uri": config.authorization_url,
                        "token_uri": config.token_url,
                    }
                },
                scopes=config.scopes,
                redirect_uri=config.redirect_uri,
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials
            return OAuthTokens(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_type="Bearer",
                expires_in=None,
                scope=" ".join(config.scopes),
                id_token=credentials.id_token,
            )
        except Exception as e:
            logger.error(f"Google token exchange failed: {e}")
            return None

    async def exchange_code(self, config: OAuthConfig, code: str) -> OAuthTokens | None:
        """Async wrapper for token exchange."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._sync_exchange_code, config, code
        )

    def _sync_fetch_user_info(
        self, config: OAuthConfig, token: str
    ) -> OAuthUserInfo | None:
        """Synchronous user info fetch using google-auth."""
        try:
            request = google_requests.Request()
            id_info = id_token.verify_oauth2_token(token, request, config.client_id)
            return OAuthUserInfo(
                provider_user_id=id_info["sub"],
                email=id_info["email"],
                full_name=id_info.get("name"),
                given_name=id_info.get("given_name"),
                family_name=id_info.get("family_name"),
                avatar_url=id_info.get("picture"),
                email_verified=id_info.get("email_verified", False),
                hosted_domain=id_info.get("hd"),
            )
        except Exception as e:
            logger.error(f"Google user info fetch failed: {e}")
            return None

    async def fetch_user_info(
        self, config: OAuthConfig, access_token: str
    ) -> OAuthUserInfo | None:
        """Async wrapper for user info fetch."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._sync_fetch_user_info, config, access_token
        )


google_oauth_provider = GoogleOAuthProvider()
