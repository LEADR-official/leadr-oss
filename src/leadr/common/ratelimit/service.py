"""Rate limit service using in-memory cache."""

from leadr.common.ratelimit.domain import IPRateLimitState
from leadr.config import settings
from leadr.infra.cache.adapters.memory import InMemoryCache


class RateLimitService:
    """Manages per-IP rate limit state for 4xx-based adaptive blocking.

    Tracks consecutive 4xx responses per IP. When threshold is exceeded,
    the IP is blocked with exponential backoff.

    Uses in-memory cache by default. Cloud deployments can provide
    Redis-backed cache for distributed rate limiting.
    """

    CACHE_PREFIX = "ratelimit:ip:"
    TTL_SECONDS = 3600  # 1 hour

    def __init__(self, cache: InMemoryCache) -> None:
        """Initialize with cache backend.

        Args:
            cache: Cache backend for storing rate limit state.
        """
        self._cache = cache

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked.

        Args:
            ip: Client IP address.

        Returns:
            True if IP is blocked, False otherwise.
        """
        state = self._cache.get(f"{self.CACHE_PREFIX}{ip}")
        if state is None:
            return False
        return state.is_blocked()

    def check_and_update(self, ip: str, status_code: int) -> bool:
        """Update state based on response status and check if blocked.

        Call this after each response. 4xx responses increment the counter,
        other responses reset it. When threshold is exceeded, IP is blocked.

        Args:
            ip: Client IP address.
            status_code: HTTP response status code.

        Returns:
            True if IP is now blocked, False otherwise.
        """
        key = f"{self.CACHE_PREFIX}{ip}"
        state = self._cache.get(key)
        if state is None:
            state = IPRateLimitState()

        # Already blocked - short circuit
        if state.is_blocked():
            return True

        # Update based on response status
        if 400 <= status_code < 500:
            state.record_4xx()

            # Check if threshold exceeded
            if state.consecutive_4xx_count >= settings.RATELIMIT_4XX_THRESHOLD:
                # Calculate block duration with exponential backoff
                exponent = state.consecutive_4xx_count - settings.RATELIMIT_4XX_THRESHOLD
                block_seconds = min(
                    settings.RATELIMIT_INITIAL_BLOCK_SECONDS * (2**exponent),
                    settings.RATELIMIT_MAX_BLOCK_SECONDS,
                )
                state.block_for_seconds(int(block_seconds))
        else:
            # Any non-4xx response resets the counter
            state.record_success()

        self._cache.set(key, state, self.TTL_SECONDS)
        return state.is_blocked()
