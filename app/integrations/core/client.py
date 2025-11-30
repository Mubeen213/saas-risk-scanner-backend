import logging
from collections.abc import AsyncGenerator
from types import TracebackType
from typing import Any, Self

import aiohttp

from app.integrations.core.exceptions import ApiRequestError, RateLimitExceededError
from app.integrations.core.pagination import PaginationStrategy
from app.integrations.core.rate_limiter import TokenBucketRateLimiter
from app.integrations.core.types import (
    ApiResponse,
    AuthContext,
    HttpMethod,
    RequestDefinition,
)

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(
        self,
        rate_limiter: TokenBucketRateLimiter | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._client: aiohttp.ClientSession | None = None
        self._rate_limiter = rate_limiter
        self._max_retries = max_retries
        logger.debug(
            "ApiClient initialized with timeout=%s, max_retries=%s",
            timeout,
            max_retries,
        )

    async def __aenter__(self) -> Self:
        logger.debug("ApiClient context entered, creating session")
        self._client = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
        logger.debug("ApiClient context exited, session closed")

    async def _get_client(self) -> aiohttp.ClientSession:
        if self._client is None or self._client.closed:
            logger.debug("Creating new aiohttp ClientSession")
            self._client = aiohttp.ClientSession(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.closed:
            logger.debug("Closing aiohttp ClientSession")
            await self._client.close()
            self._client = None

    async def execute(
        self,
        request: RequestDefinition,
        auth_context: AuthContext,
    ) -> ApiResponse:
        if self._rate_limiter:
            await self._rate_limiter.acquire(request.cost)

        headers = self._build_headers(request, auth_context)
        response = await self._execute_with_retry(request, headers)
        return response

    async def execute_paginated(
        self,
        request: RequestDefinition,
        auth_context: AuthContext,
        paginator: PaginationStrategy,
    ) -> AsyncGenerator[list[Any], None]:
        current_params = {**request.params}
        logger.info(
            f"Starting paginated request to {request.url} with params {current_params}"
        )
        if hasattr(paginator, "get_initial_params"):
            initial_params = paginator.get_initial_params()
            current_params = {**initial_params, **current_params}

        while True:
            current_request = RequestDefinition(
                method=request.method,
                url=request.url,
                params=current_params,
                headers=request.headers,
                body=request.body,
                cost=request.cost,
            )

            response = await self.execute(current_request, auth_context)

            if not response.is_success:
                raise ApiRequestError(
                    response.status_code, f"API request failed: {response.data}"
                )

            items = paginator.extract_items(response.data)
            if items:
                yield items

            next_params = paginator.get_next_params(response.data, current_params)
            if next_params is None:
                break

            current_params = next_params

    def _build_headers(
        self, request: RequestDefinition, auth_context: AuthContext
    ) -> dict[str, str]:
        headers = {
            "Authorization": auth_context.authorization_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(request.headers)
        return headers

    async def _execute_with_retry(
        self, request: RequestDefinition, headers: dict[str, str]
    ) -> ApiResponse:
        last_exception: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} for request to {request.url}")
                response = await self._make_request(request, headers)

                if response.is_rate_limited:
                    retry_after = self._parse_retry_after(response.headers)
                    if attempt < self._max_retries - 1 and self._rate_limiter:
                        logger.warning(
                            f"Rate limited, waiting {retry_after}s before retry {attempt + 1}"
                        )
                        await self._rate_limiter.wait_for_retry(retry_after)
                        continue
                    raise RateLimitExceededError(retry_after)

                if response.status_code >= 500 and attempt < self._max_retries - 1:
                    logger.warning(
                        f"Server error {response.status_code}, retry {attempt + 1}"
                    )
                    continue

                return response

            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"Request error: {e}, retry {attempt + 1}")
                if attempt == self._max_retries - 1:
                    raise ApiRequestError(500, str(e)) from e

        raise ApiRequestError(500, str(last_exception))

    async def _make_request(
        self, request: RequestDefinition, headers: dict[str, str]
    ) -> ApiResponse:
        http_method = request.method.value.lower()
        client = await self._get_client()

        kwargs: dict[str, Any] = {
            "headers": headers,
            "params": request.params or None,
        }

        if request.body and request.method in (
            HttpMethod.POST,
            HttpMethod.PUT,
            HttpMethod.PATCH,
        ):
            kwargs["json"] = request.body

        logger.debug(
            f"Making {request.method.value} request to {request.url} with params {request.params} and headers {len(request.headers)}"
        )
        async with client.request(http_method, request.url, **kwargs) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                data = {}

            return ApiResponse(
                status_code=response.status,
                data=data,
                headers={k: v for k, v in response.headers.items()},
            )

    def _parse_retry_after(self, headers: dict[str, str]) -> int | None:
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        logger.debug(f"Parsing Retry-After header: {retry_after}")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        return None
