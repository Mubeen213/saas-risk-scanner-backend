import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    requests_per_second: float = 10.0
    burst_size: int = 20
    retry_after_default: int = 60


class TokenBucketRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._tokens: float = float(self.config.burst_size)
        self._last_update: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, cost: int = 1) -> None:
        async with self._lock:
            await self._wait_for_tokens(cost)
            self._tokens -= cost

    async def _wait_for_tokens(self, cost: int) -> None:
        while True:
            self._refill()
            if self._tokens >= cost:
                return
            tokens_needed = cost - self._tokens
            wait_time = tokens_needed / self.config.requests_per_second
            await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        new_tokens = elapsed * self.config.requests_per_second
        self._tokens = min(self._tokens + new_tokens, float(self.config.burst_size))

    async def wait_for_retry(self, retry_after: int | None = None) -> None:
        wait_time = retry_after or self.config.retry_after_default
        await asyncio.sleep(wait_time)


@dataclass
class ProviderRateLimits:
    provider_slug: str
    limiters: dict[str, TokenBucketRateLimiter] = field(default_factory=dict)

    def get_limiter(
        self, endpoint_key: str, config: RateLimitConfig | None = None
    ) -> TokenBucketRateLimiter:
        if endpoint_key not in self.limiters:
            self.limiters[endpoint_key] = TokenBucketRateLimiter(config)
        return self.limiters[endpoint_key]


class RateLimiterRegistry:
    def __init__(self):
        self._providers: dict[str, ProviderRateLimits] = {}

    def get_provider_limits(self, provider_slug: str) -> ProviderRateLimits:
        if provider_slug not in self._providers:
            self._providers[provider_slug] = ProviderRateLimits(
                provider_slug=provider_slug
            )
        return self._providers[provider_slug]

    def get_limiter(
        self,
        provider_slug: str,
        endpoint_key: str,
        config: RateLimitConfig | None = None,
    ) -> TokenBucketRateLimiter:
        provider_limits = self.get_provider_limits(provider_slug)
        return provider_limits.get_limiter(endpoint_key, config)


rate_limiter_registry = RateLimiterRegistry()
