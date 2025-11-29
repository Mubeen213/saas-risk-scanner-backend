from abc import ABC, abstractmethod

from app.oauth.types import OAuthConfig, OAuthTokens, OAuthUserInfo


class OAuthProvider(ABC):

    @property
    @abstractmethod
    def provider_slug(self) -> str:
        pass

    @abstractmethod
    def build_authorization_url(self, config: OAuthConfig, state: str) -> str:
        pass

    @abstractmethod
    async def exchange_code(self, config: OAuthConfig, code: str) -> OAuthTokens | None:
        pass

    @abstractmethod
    async def fetch_user_info(
        self, config: OAuthConfig, access_token: str
    ) -> OAuthUserInfo | None:
        pass

