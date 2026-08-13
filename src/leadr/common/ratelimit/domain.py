"""Rate limit state domain model."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class IPRateLimitState:
    """Tracks rate limit state for a single IP address.

    Used for 4xx-based adaptive rate limiting. When an IP accumulates
    too many consecutive 4xx responses, it gets temporarily blocked.
    """

    consecutive_4xx_count: int = 0
    blocked_until: datetime | None = None

    def record_success(self) -> None:
        """Reset counter on successful (non-4xx) response."""
        self.consecutive_4xx_count = 0

    def record_4xx(self) -> None:
        """Increment counter on 4xx response."""
        self.consecutive_4xx_count += 1

    def is_blocked(self) -> bool:
        """Check if currently blocked."""
        if self.blocked_until is None:
            return False
        return datetime.now(UTC) < self.blocked_until

    def block_for_seconds(self, seconds: int) -> None:
        """Block for specified duration."""
        self.blocked_until = datetime.now(UTC) + timedelta(seconds=seconds)
