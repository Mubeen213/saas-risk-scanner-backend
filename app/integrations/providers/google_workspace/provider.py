import logging
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp

from app.integrations.core.client import ApiClient
from app.integrations.core.interfaces import IWorkspaceProvider
from app.integrations.core.pagination import PaginationStrategy
from app.integrations.core.rate_limiter import RateLimitConfig, rate_limiter_registry
from app.integrations.core.types import (
    AuthContext,
    HttpMethod,
    RequestDefinition,
    SyncStep,
    TokenResponse,
    UnifiedGroup,
    UnifiedGroupMembership,
    UnifiedToken,
    UnifiedTokenEvent,
    UnifiedUser,
)
from app.integrations.providers.google_workspace.adapters import (
    adapt_google_groups,
    adapt_google_members,
    adapt_google_token_events,
    adapt_google_users,
    adapt_google_user_tokens,
)
from app.integrations.providers.google_workspace.constants import (
    GOOGLE_GROUP_MEMBERS_ENDPOINT,
    GOOGLE_GROUPS_ENDPOINT,
    GOOGLE_OAUTH_TOKEN_URL,
    GOOGLE_RATE_LIMITS,
    GOOGLE_TOKEN_ACTIVITIES_ENDPOINT,
    GOOGLE_USERS_ENDPOINT,
    GOOGLE_USER_TOKENS_ENDPOINT,
    GOOGLE_WORKSPACE_PROVIDER_SLUG,
)
from app.integrations.providers.google_workspace.paginators import (
    get_paginator_for_step,
)

logger = logging.getLogger(__name__)


class GoogleWorkspaceProvider(IWorkspaceProvider):
    def __init__(self):
        self._api_client: ApiClient | None = None

    @property
    def provider_slug(self) -> str:
        return GOOGLE_WORKSPACE_PROVIDER_SLUG

    def get_sync_pipeline(self) -> list[SyncStep]:
        return [
            SyncStep.USERS,
            SyncStep.GROUPS,
            SyncStep.GROUP_MEMBERS,
            SyncStep.TOKEN_EVENTS,
        ]

    def get_paginator(self, step: SyncStep) -> PaginationStrategy:
        return get_paginator_for_step(step)

    def get_request_definition(
        self, step: SyncStep, params: dict[str, Any]
    ) -> RequestDefinition:
        endpoints: dict[SyncStep, str] = {
            SyncStep.USERS: GOOGLE_USERS_ENDPOINT,
            SyncStep.GROUPS: GOOGLE_GROUPS_ENDPOINT,
            SyncStep.GROUP_MEMBERS: GOOGLE_GROUP_MEMBERS_ENDPOINT.format(
                group_key=params.get("group_key", "")
            ),
            SyncStep.TOKEN_EVENTS: GOOGLE_TOKEN_ACTIVITIES_ENDPOINT,
            SyncStep.USER_TOKENS: GOOGLE_USER_TOKENS_ENDPOINT.format(
                user_key=params.get("user_key", "")
            ),
        }

        url = endpoints.get(step, GOOGLE_USERS_ENDPOINT)
        request_params = {"customer": "my_customer"}

        if step == SyncStep.TOKEN_EVENTS and params.get("start_time"):
            request_params["startTime"] = params["start_time"]

        return RequestDefinition(
            method=HttpMethod.GET,
            url=url,
            params=request_params,
        )

    async def exchange_code_for_tokens(
        self, code: str, client_id: str, client_secret: str, redirect_uri: str
    ) -> TokenResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
            ) as response:
                response.raise_for_status()
                data = await response.json()

                return TokenResponse(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope"),
                )

    async def refresh_access_token(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> TokenResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            ) as response:
                response.raise_for_status()
                data = await response.json()

                return TokenResponse(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope"),
                )

    async def fetch_users(
        self, auth_context: AuthContext
    ) -> AsyncGenerator[list[UnifiedUser], None]:
        logger.debug("Starting to fetch users from Google Workspace")
        request = self.get_request_definition(SyncStep.USERS, {})
        paginator = self.get_paginator(SyncStep.USERS)

        async with self._create_api_client(SyncStep.USERS) as client:
            async for raw_users in client.execute_paginated(
                request, auth_context, paginator
            ):
                logger.debug(f"Fetched batch of {len(raw_users)} users")
                yield adapt_google_users(raw_users)
        logger.debug("Finished fetching users from Google Workspace")

    async def fetch_groups(
        self, auth_context: AuthContext
    ) -> AsyncGenerator[list[UnifiedGroup], None]:
        logger.debug("Starting to fetch groups from Google Workspace")
        request = self.get_request_definition(SyncStep.GROUPS, {})
        paginator = self.get_paginator(SyncStep.GROUPS)

        async with self._create_api_client(SyncStep.GROUPS) as client:
            async for raw_groups in client.execute_paginated(
                request, auth_context, paginator
            ):
                logger.debug(f"Fetched batch of {len(raw_groups)} groups")
                yield adapt_google_groups(raw_groups)
        logger.debug("Finished fetching groups from Google Workspace")

    async def fetch_group_members(
        self, auth_context: AuthContext, group_id: str
    ) -> AsyncGenerator[list[UnifiedGroupMembership], None]:
        logger.debug(f"Starting to fetch members for group: {group_id}")
        request = self.get_request_definition(
            SyncStep.GROUP_MEMBERS, {"group_key": group_id}
        )
        paginator = self.get_paginator(SyncStep.GROUP_MEMBERS)

        async with self._create_api_client(SyncStep.GROUP_MEMBERS) as client:
            async for raw_members in client.execute_paginated(
                request, auth_context, paginator
            ):
                logger.debug(
                    f"Fetched batch of {len(raw_members)} members for group {group_id}"
                )
                yield adapt_google_members(raw_members, group_id)
        logger.debug(f"Finished fetching members for group: {group_id}")

    async def fetch_token_events(
        self, auth_context: AuthContext, start_time: str | None = None
    ) -> AsyncGenerator[list[UnifiedTokenEvent], None]:
        logger.debug(f"Starting to fetch token events, start_time: {start_time}")
        request = self.get_request_definition(
            SyncStep.TOKEN_EVENTS, {"start_time": start_time}
        )
        paginator = self.get_paginator(SyncStep.TOKEN_EVENTS)

        async with self._create_api_client(SyncStep.TOKEN_EVENTS) as client:
            async for raw_events in client.execute_paginated(
                request, auth_context, paginator
            ):
                logger.debug(f"Fetched batch of {len(raw_events)} token events")
                yield adapt_google_token_events(raw_events)
        logger.debug("Finished fetching token events")

    async def fetch_user_tokens(
        self, auth_context: AuthContext, user_id: str
    ) -> AsyncGenerator[list[UnifiedToken], None]:
        # Tokens endpoint is not paginated in the same way as others, usually returns all or has specific pagination?
        # Google Directory API tokens.list doesn't seem to explicitly support pagination in the simple sense or it's rarely large.
        # But we should respect if it does. Standard list usually has nextPageToken.
        
        logger.debug(f"Starting to fetch tokens for user: {user_id}")
        request = self.get_request_definition(
            SyncStep.USER_TOKENS, {"user_key": user_id}
        )
        # We can reuse a generic paginator or simple execution if pagination isn't critical or different.
        # For safety, let's assume it might be paginated.
        paginator = self.get_paginator(SyncStep.USER_TOKENS)

        async with self._create_api_client(SyncStep.USER_TOKENS) as client:
            async for raw_tokens in client.execute_paginated(
                request, auth_context, paginator
            ):
                yield adapt_google_user_tokens(raw_tokens)
        logger.debug(f"Finished fetching tokens for user: {user_id}")

    async def revoke_app_access(
        self, auth_context: AuthContext, user_id: str, client_id: str
    ) -> bool:
        from app.integrations.providers.google_workspace.constants import (
            GOOGLE_USER_TOKENS_ENDPOINT,
        )

        logger.debug(
            f"Revoking app access for user: {user_id}, client_id: {client_id}"
        )
        url = GOOGLE_USER_TOKENS_ENDPOINT.format(user_key=user_id) + f"/{client_id}"

        request = RequestDefinition(
            method=HttpMethod.DELETE,
            url=url,
        )

        async with self._create_api_client(SyncStep.USER_TOKENS) as client:
            response = await client.execute(request, auth_context)
            success = response.is_success
            logger.debug(f"Revoke app access result for user {user_id}: {success}")
            return success

    def _create_api_client(self, step: SyncStep) -> ApiClient:
        rate_config_data = GOOGLE_RATE_LIMITS.get(step.value, {})
        rate_config = RateLimitConfig(**rate_config_data) if rate_config_data else None

        rate_limiter = rate_limiter_registry.get_limiter(
            self.provider_slug, step.value, rate_config
        )

        logger.debug(f"Creating ApiClient for step: {step.value}")
        return ApiClient(rate_limiter=rate_limiter)


google_workspace_provider = GoogleWorkspaceProvider()
