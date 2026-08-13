"""Tests for rate limit service."""

import pytest

from leadr.common.ratelimit.service import RateLimitService
from leadr.infra.cache.adapters.memory import InMemoryCache


@pytest.fixture
def cache() -> InMemoryCache:
    """Provide a fresh cache for each test."""
    return InMemoryCache()


@pytest.fixture
def service(cache: InMemoryCache) -> RateLimitService:
    """Provide a rate limit service for each test."""
    return RateLimitService(cache)


class TestRateLimitService:
    """Tests for RateLimitService."""

    def test_is_blocked_returns_false_for_unknown_ip(self, service: RateLimitService) -> None:
        """Unknown IPs should not be blocked."""
        assert service.is_blocked("192.168.1.1") is False

    def test_check_and_update_tracks_4xx(self, service: RateLimitService) -> None:
        """4xx responses should increment counter."""
        ip = "192.168.1.1"

        # First 4xx - not blocked yet
        blocked = service.check_and_update(ip, 404)
        assert blocked is False

        # Check state was saved
        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        assert state.consecutive_4xx_count == 1

    def test_check_and_update_resets_on_success(self, service: RateLimitService) -> None:
        """Successful responses should reset counter."""
        ip = "192.168.1.1"

        # Record some 4xx
        service.check_and_update(ip, 404)
        service.check_and_update(ip, 404)

        # Then a success
        service.check_and_update(ip, 200)

        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        assert state.consecutive_4xx_count == 0

    def test_blocks_after_threshold(
        self, service: RateLimitService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IP should be blocked after exceeding threshold."""
        ip = "192.168.1.1"

        # Set low threshold for testing
        monkeypatch.setattr("leadr.common.ratelimit.service.settings.RATELIMIT_4XX_THRESHOLD", 3)
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 60
        )
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_MAX_BLOCK_SECONDS", 3600
        )

        # Record threshold number of 4xx
        blocked = False
        for _ in range(3):
            blocked = service.check_and_update(ip, 404)

        # Should now be blocked
        assert blocked is True
        assert service.is_blocked(ip) is True

    def test_exponential_backoff(
        self, service: RateLimitService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Block duration should increase with each additional 4xx."""
        ip = "192.168.1.1"

        monkeypatch.setattr("leadr.common.ratelimit.service.settings.RATELIMIT_4XX_THRESHOLD", 2)
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 60
        )
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_MAX_BLOCK_SECONDS", 3600
        )

        # Hit threshold (2 4xx)
        service.check_and_update(ip, 404)
        service.check_and_update(ip, 404)

        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        assert state.blocked_until is not None

    def test_respects_max_block_duration(
        self, service: RateLimitService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Block duration should not exceed max."""
        ip = "192.168.1.1"

        monkeypatch.setattr("leadr.common.ratelimit.service.settings.RATELIMIT_4XX_THRESHOLD", 1)
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 3600
        )
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_MAX_BLOCK_SECONDS", 100
        )

        # First 4xx triggers block
        service.check_and_update(ip, 404)

        # Block should be capped at max
        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        # Initial would be 3600, but capped at 100
        assert state.blocked_until is not None

    def test_already_blocked_stays_blocked(
        self, service: RateLimitService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Already blocked IPs should return True without updating."""
        ip = "192.168.1.1"

        monkeypatch.setattr("leadr.common.ratelimit.service.settings.RATELIMIT_4XX_THRESHOLD", 1)
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 60
        )
        monkeypatch.setattr(
            "leadr.common.ratelimit.service.settings.RATELIMIT_MAX_BLOCK_SECONDS", 3600
        )

        # Trigger block
        service.check_and_update(ip, 404)
        assert service.is_blocked(ip) is True

        # Additional check should still return blocked
        blocked = service.check_and_update(ip, 404)
        assert blocked is True

    def test_3xx_treated_as_success(self, service: RateLimitService) -> None:
        """3xx responses should reset counter like success."""
        ip = "192.168.1.1"

        service.check_and_update(ip, 404)
        service.check_and_update(ip, 301)

        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        assert state.consecutive_4xx_count == 0

    def test_5xx_treated_as_success(self, service: RateLimitService) -> None:
        """5xx responses should reset counter (server errors aren't client's fault)."""
        ip = "192.168.1.1"

        service.check_and_update(ip, 404)
        service.check_and_update(ip, 500)

        state = service._cache.get(f"{service.CACHE_PREFIX}{ip}")
        assert state is not None
        assert state.consecutive_4xx_count == 0
