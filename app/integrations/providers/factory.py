from app.integrations.core.interfaces import IWorkspaceProvider
from app.integrations.providers.google_workspace.provider import google_workspace_provider

_PROVIDERS: dict[str, IWorkspaceProvider] = {
    "google-workspace": google_workspace_provider,
}


def get_provider_by_slug(slug: str) -> IWorkspaceProvider | None:
    return _PROVIDERS.get(slug)
