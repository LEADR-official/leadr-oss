"""Anti-cheat enums for flag types, confidence levels, and actions."""

from enum import Enum


class TrustTier(str, Enum):
    """Trust tier for devices/users, determining anti-cheat thresholds.

    Different tiers have different rate limits and detection thresholds:
    - Tier A (Trusted): Most lenient thresholds, highest rate limits
    - Tier B (Verified): Moderate thresholds and rate limits
    - Tier C (Unverified): Strictest thresholds, lowest rate limits
    """

    A = "a"
    """Tier A - Trusted devices with verified attestation."""

    B = "b"
    """Tier B - Verified devices without full attestation."""

    C = "c"
    """Tier C - Unverified or new devices."""


class FlagType(str, Enum):
    """Type of anti-cheat flag detected.

    Each flag type represents a different detection tactic used to identify
    potentially suspicious score submissions.
    """

    RATE_LIMIT = "rate_limit"
    """Score submission exceeds rate limits for the user/board."""

    DUPLICATE = "duplicate"
    """Identical score value submitted multiple times in short time window."""

    VELOCITY = "velocity"
    """Submissions are happening too quickly (< 2 seconds apart)."""

    OUTLIER = "outlier"
    """Score is statistically anomalous compared to board distribution."""

    IMPOSSIBLE_VALUE = "impossible_value"
    """Score contains mathematically impossible value (negative, NaN, etc)."""

    PATTERN = "pattern"
    """Suspicious pattern detected in submission history (all round numbers, etc)."""

    PROGRESSION = "progression"
    """Unrealistic improvement percentage between submissions."""

    CLUSTER = "cluster"
    """Multiple users submitting identical scores in short time window."""

    MANUAL = "manual"
    """Admin manually flagged this score for review."""


class FlagConfidence(str, Enum):
    """Confidence level for anti-cheat detection.

    Determines the action taken when a flag is raised:
    - HIGH: Auto-reject submission
    - MEDIUM: Flag for manual review, accept submission
    - LOW: Log for analysis, accept submission
    """

    LOW = "low"
    """Low confidence detection - log but accept."""

    MEDIUM = "medium"
    """Medium confidence detection - flag for review but accept."""

    HIGH = "high"
    """High confidence detection - reject submission."""


class FlagAction(str, Enum):
    """Action to take based on anti-cheat analysis.

    Determines how the score submission should be handled.
    """

    ACCEPT = "accept"
    """Accept the score submission without any flags."""

    FLAG = "flag"
    """Accept the score but flag it for manual review."""

    REJECT = "reject"
    """Reject the score submission (do not save to database)."""


class ScoreFlagStatus(str, Enum):
    """Status of a score flag review.

    Indicates whether a flag has been reviewed and what decision was made.
    """

    PENDING = "pending"
    """Flag has not been reviewed yet."""

    CONFIRMED_CHEAT = "confirmed_cheat"
    """Admin confirmed this is cheating behavior."""

    FALSE_POSITIVE = "false_positive"
    """Admin determined this was legitimate gameplay."""

    DISMISSED = "dismissed"
    """Admin dismissed the flag without a specific determination."""


class ScoreStatus(str, Enum):
    """Lifecycle status of a score in the anti-cheat workflow.

    Tracks the score from submission through review, determining visibility
    on leaderboards.
    """

    PROVISIONAL = "provisional"
    """Initial transient state before anti-cheat check completes."""

    ACTIVE = "active"
    """Score passed anti-cheat checks and is visible on leaderboards."""

    UNDER_REVIEW = "under_review"
    """Score was flagged by anti-cheat, pending admin review. Still visible."""

    REJECTED = "rejected"
    """Admin confirmed cheating - hidden from leaderboards."""
