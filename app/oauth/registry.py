from app.oauth.base import OAuthProvider
from app.oauth.providers.google import google_oauth_provider


class OAuthProviderRegistry:
    """Registry for OAuth providers."""

    def __init__(self) -> None:
        self._providers: dict[str, OAuthProvider] = {}

    def register(self, provider: OAuthProvider) -> None:
        """Register an OAuth provider."""
        self._providers[provider.provider_slug] = provider

    def get(self, provider_slug: str) -> OAuthProvider | None:
        """Get an OAuth provider by slug."""
        return self._providers.get(provider_slug)

    def list_providers(self) -> list[str]:
        """List all registered provider slugs."""
        return list(self._providers.keys())


oauth_provider_registry = OAuthProviderRegistry()

# Register built-in providers
oauth_provider_registry.register(google_oauth_provider)
