from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.integrations.core.pagination import PaginationStrategy
from app.integrations.core.types import (
    AuthContext,
    RequestDefinition,
    SyncStep,
    TokenResponse,
    UnifiedGroup,
    UnifiedGroupMembership,
    UnifiedTokenEvent,
    UnifiedUser,
)


class IWorkspaceProvider(ABC):
    @property
    @abstractmethod
    def provider_slug(self) -> str:
        pass

    @abstractmethod
    def get_sync_pipeline(self) -> list[SyncStep]:
        pass

    @abstractmethod
    def get_paginator(self, step: SyncStep) -> PaginationStrategy:
        pass

    @abstractmethod
    def get_request_definition(
        self, step: SyncStep, params: dict[str, Any]
    ) -> RequestDefinition:
        pass

    @abstractmethod
    async def refresh_access_token(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> TokenResponse:
        pass

    @abstractmethod
    async def fetch_users(
        self, auth_context: AuthContext
    ) -> AsyncGenerator[list[UnifiedUser], None]:
        pass

    @abstractmethod
    async def fetch_groups(
        self, auth_context: AuthContext
    ) -> AsyncGenerator[list[UnifiedGroup], None]:
        pass

    @abstractmethod
    async def fetch_group_members(
        self, auth_context: AuthContext, group_id: str
    ) -> AsyncGenerator[list[UnifiedGroupMembership], None]:
        pass

    @abstractmethod
    async def fetch_token_events(
        self, auth_context: AuthContext, start_time: str | None = None
    ) -> AsyncGenerator[list[UnifiedTokenEvent], None]:
        pass

    @abstractmethod
    async def revoke_app_access(
        self, auth_context: AuthContext, user_id: str, client_id: str
    ) -> bool:
        pass


class ICredentialsManager(ABC):
    @abstractmethod
    async def get_valid_credentials(self, connection_id: int) -> AuthContext:
        pass

    @abstractmethod
    async def store_credentials(
        self,
        connection_id: int,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None,
    ) -> None:
        pass

    @abstractmethod
    async def handle_token_error(self, connection_id: int, error_code: str) -> bool:
        pass
