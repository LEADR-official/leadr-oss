"""Anti-cheat service for detecting suspicious score submissions."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import BoardID, DeviceID
from leadr.config import settings
from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType, TrustTier
from leadr.scores.domain.anti_cheat.models import AntiCheatResult, ScoreSubmissionMeta
from leadr.scores.domain.score import Score
from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository


class AntiCheatService:
    """Service for anti-cheat detection and analysis.

    Implements various detection tactics to identify suspicious score submissions:
    - Rate limiting: Prevents excessive submissions per device/board
    - Duplicate detection: Identifies repeated identical scores
    - Velocity detection: Detects rapid-fire submissions
    - Statistical outliers: Identifies anomalous scores
    - Pattern detection: Finds suspicious submission patterns
    """

    def __init__(self, session: AsyncSession):
        """Initialize anti-cheat service.

        Args:
            session: Database session for querying metadata
        """
        self.session = session
        self.meta_repo = ScoreSubmissionMetaRepository(session)

    async def check_submission(
        self,
        score: Score,
        trust_tier: TrustTier,
        device_id: DeviceID,
        board_id: BoardID,
    ) -> AntiCheatResult:
        """Check a score submission for suspicious patterns.

        Args:
            score: Score being submitted
            trust_tier: Trust tier of the device (A/B/C)
            device_id: ID of the device submitting the score
            board_id: ID of the board being submitted to

        Returns:
            AntiCheatResult indicating action to take (ACCEPT/FLAG/REJECT)
        """
        # Fetch submission metadata once for all checks
        submission_meta = await self.meta_repo.get_by_device_and_board(device_id, board_id)

        # Check rate limiting
        rate_limit_result = await self._check_rate_limit(
            submission_meta=submission_meta,
            trust_tier=trust_tier,
        )

        if rate_limit_result.action != FlagAction.ACCEPT:
            return rate_limit_result

        # Check for duplicate scores
        duplicate_result = await self._check_duplicate(
            score=score,
            submission_meta=submission_meta,
        )

        if duplicate_result.action != FlagAction.ACCEPT:
            return duplicate_result

        # Check for velocity (rapid-fire submissions)
        velocity_result = await self._check_velocity(
            submission_meta=submission_meta,
        )

        if velocity_result.action != FlagAction.ACCEPT:
            return velocity_result

        # All checks passed
        return AntiCheatResult(action=FlagAction.ACCEPT)

    async def _check_rate_limit(
        self,
        submission_meta: ScoreSubmissionMeta | None,
        trust_tier: TrustTier,
    ) -> AntiCheatResult:
        """Check if device exceeds rate limit for this board.

        Args:
            submission_meta: Pre-fetched submission metadata (or None for first submission)
            trust_tier: Trust tier determining rate limit threshold

        Returns:
            AntiCheatResult with ACCEPT or REJECT action
        """
        # Get rate limit for this trust tier
        rate_limits = {
            TrustTier.A: settings.ANTICHEAT_RATE_LIMIT_TIER_A,
            TrustTier.B: settings.ANTICHEAT_RATE_LIMIT_TIER_B,
            TrustTier.C: settings.ANTICHEAT_RATE_LIMIT_TIER_C,
        }
        limit = rate_limits[trust_tier]

        # First submission - always accept
        if submission_meta is None:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if last submission was within 1 hour (sliding window)
        now = datetime.now(UTC)
        one_hour_ago = now - timedelta(hours=1)

        # If last submission was > 1 hour ago, window expired - accept
        if submission_meta.last_submission_at < one_hour_ago:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if submission count within window exceeds limit
        if submission_meta.submission_count >= limit:
            return AntiCheatResult(
                action=FlagAction.REJECT,
                flag_type=FlagType.RATE_LIMIT,
                confidence=FlagConfidence.HIGH,
                reason=f"Device exceeded rate limit of {limit} submissions per hour for this board",
                metadata={
                    "limit": limit,
                    "submissions_count": submission_meta.submission_count,
                    "trust_tier": trust_tier.value,
                    "window_start": submission_meta.last_submission_at.isoformat(),
                },
            )

        # Under limit - accept
        return AntiCheatResult(action=FlagAction.ACCEPT)

    async def _check_duplicate(
        self,
        score: Score,
        submission_meta: ScoreSubmissionMeta | None,
    ) -> AntiCheatResult:
        """Check if score is a duplicate of recently submitted score.

        Args:
            score: Score being submitted
            submission_meta: Pre-fetched submission metadata (or None for first submission)

        Returns:
            AntiCheatResult with ACCEPT or FLAG action
        """
        # First submission - always accept
        if submission_meta is None or submission_meta.last_score_value is None:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if score value matches last submission
        if score.value == submission_meta.last_score_value:
            # Check if within duplicate detection window
            now = datetime.now(UTC)
            window_seconds = settings.ANTICHEAT_DUPLICATE_WINDOW_SECONDS
            window_start = now - timedelta(seconds=window_seconds)

            if submission_meta.last_submission_at >= window_start:
                # Duplicate within window - flag for review
                return AntiCheatResult(
                    action=FlagAction.FLAG,
                    flag_type=FlagType.DUPLICATE,
                    confidence=FlagConfidence.MEDIUM,
                    reason=(
                        f"Duplicate score value ({score.value}) submitted "
                        f"within {window_seconds} seconds"
                    ),
                    metadata={
                        "score_value": score.value,
                        "previous_submission_at": submission_meta.last_submission_at.isoformat(),
                        "window_seconds": window_seconds,
                    },
                )

        # Not a duplicate or outside window - accept
        return AntiCheatResult(action=FlagAction.ACCEPT)

    async def _check_velocity(
        self,
        submission_meta: ScoreSubmissionMeta | None,
    ) -> AntiCheatResult:
        """Check if submissions are happening too rapidly (rapid-fire detection).

        Args:
            submission_meta: Pre-fetched submission metadata (or None for first submission)

        Returns:
            AntiCheatResult with ACCEPT or FLAG action
        """
        # First submission - always accept
        if submission_meta is None:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check time since last submission
        now = datetime.now(UTC)
        time_since_last = (now - submission_meta.last_submission_at).total_seconds()
        velocity_threshold = settings.ANTICHEAT_VELOCITY_THRESHOLD_SECONDS

        # If submitting too quickly - flag as suspicious
        if time_since_last < velocity_threshold:
            return AntiCheatResult(
                action=FlagAction.FLAG,
                flag_type=FlagType.VELOCITY,
                confidence=FlagConfidence.HIGH,
                reason=(
                    f"Rapid-fire submission detected: {time_since_last:.2f}s "
                    f"between submissions (threshold: {velocity_threshold}s)"
                ),
                metadata={
                    "time_since_last_submission": time_since_last,
                    "velocity_threshold": velocity_threshold,
                    "last_submission_at": submission_meta.last_submission_at.isoformat(),
                },
            )

        # Normal pace - accept
        return AntiCheatResult(action=FlagAction.ACCEPT)
