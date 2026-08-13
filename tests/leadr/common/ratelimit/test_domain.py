"""Tests for rate limit domain model."""

from datetime import UTC, datetime, timedelta

from leadr.common.ratelimit.domain import IPRateLimitState


class TestIPRateLimitState:
    """Tests for IPRateLimitState dataclass."""

    def test_initial_state_not_blocked(self) -> None:
        """New state should not be blocked."""
        state = IPRateLimitState()
        assert state.is_blocked() is False
        assert state.consecutive_4xx_count == 0
        assert state.blocked_until is None

    def test_record_4xx_increments_count(self) -> None:
        """Recording a 4xx should increment the counter."""
        state = IPRateLimitState()
        state.record_4xx()
        assert state.consecutive_4xx_count == 1
        state.record_4xx()
        assert state.consecutive_4xx_count == 2

    def test_record_success_resets_count(self) -> None:
        """Recording a success should reset the counter."""
        state = IPRateLimitState(consecutive_4xx_count=5)
        state.record_success()
        assert state.consecutive_4xx_count == 0

    def test_block_for_seconds_sets_blocked_until(self) -> None:
        """Blocking should set blocked_until to future time."""
        state = IPRateLimitState()
        before = datetime.now(UTC)
        state.block_for_seconds(60)
        after = datetime.now(UTC)

        assert state.blocked_until is not None
        assert state.blocked_until >= before + timedelta(seconds=60)
        assert state.blocked_until <= after + timedelta(seconds=60)

    def test_is_blocked_returns_true_during_block(self) -> None:
        """is_blocked should return True during block period."""
        state = IPRateLimitState()
        state.block_for_seconds(60)
        assert state.is_blocked() is True

    def test_is_blocked_returns_false_after_block_expires(self) -> None:
        """is_blocked should return False after block expires."""
        state = IPRateLimitState()
        # Set blocked_until to past
        state.blocked_until = datetime.now(UTC) - timedelta(seconds=1)
        assert state.is_blocked() is False

    def test_is_blocked_returns_false_when_not_set(self) -> None:
        """is_blocked should return False when blocked_until is None."""
        state = IPRateLimitState()
        assert state.is_blocked() is False
