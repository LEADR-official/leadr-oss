"""Anti-cheat enums for flag types, confidence levels, and actions."""

from enum import Enum


class TrustTier(str, Enum):
    """Trust tier for devices/users, determining anti-cheat thresholds.

    Different tiers have different rate limits and detection thresholds:
    - Tier A (Trusted): Most lenient thresholds, highest rate limits
    - Tier B (Verified): Moderate thresholds and rate limits
    - Tier C (Unverified): Strictest thresholds, lowest rate limits
    """

    A = "A"
    """Tier A - Trusted devices with verified attestation."""

    B = "B"
    """Tier B - Verified devices without full attestation."""

    C = "C"
    """Tier C - Unverified or new devices."""


class FlagType(str, Enum):
    """Type of anti-cheat flag detected.

    Each flag type represents a different detection tactic used to identify
    potentially suspicious score submissions.
    """

    RATE_LIMIT = "RATE_LIMIT"
    """Score submission exceeds rate limits for the user/board."""

    DUPLICATE = "DUPLICATE"
    """Identical score value submitted multiple times in short time window."""

    VELOCITY = "VELOCITY"
    """Submissions are happening too quickly (< 2 seconds apart)."""

    OUTLIER = "OUTLIER"
    """Score is statistically anomalous compared to board distribution."""

    IMPOSSIBLE_VALUE = "IMPOSSIBLE_VALUE"
    """Score contains mathematically impossible value (negative, NaN, etc)."""

    PATTERN = "PATTERN"
    """Suspicious pattern detected in submission history (all round numbers, etc)."""

    PROGRESSION = "PROGRESSION"
    """Unrealistic improvement percentage between submissions."""

    CLUSTER = "CLUSTER"
    """Multiple users submitting identical scores in short time window."""


class FlagConfidence(str, Enum):
    """Confidence level for anti-cheat detection.

    Determines the action taken when a flag is raised:
    - HIGH: Auto-reject submission
    - MEDIUM: Flag for manual review, accept submission
    - LOW: Log for analysis, accept submission
    """

    LOW = "LOW"
    """Low confidence detection - log but accept."""

    MEDIUM = "MEDIUM"
    """Medium confidence detection - flag for review but accept."""

    HIGH = "HIGH"
    """High confidence detection - reject submission."""


class FlagAction(str, Enum):
    """Action to take based on anti-cheat analysis.

    Determines how the score submission should be handled.
    """

    ACCEPT = "ACCEPT"
    """Accept the score submission without any flags."""

    FLAG = "FLAG"
    """Accept the score but flag it for manual review."""

    REJECT = "REJECT"
    """Reject the score submission (do not save to database)."""
