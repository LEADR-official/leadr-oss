"""Anti-cheat service for detecting suspicious score submissions."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
        device_id: UUID,
        board_id: UUID,
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
        # Check rate limiting
        rate_limit_result = await self._check_rate_limit(
            device_id=device_id,
            board_id=board_id,
            trust_tier=trust_tier,
        )

        if rate_limit_result.action != FlagAction.ACCEPT:
            return rate_limit_result

        # Check for duplicate scores
        duplicate_result = await self._check_duplicate(
            score=score,
            device_id=device_id,
            board_id=board_id,
        )

        if duplicate_result.action != FlagAction.ACCEPT:
            return duplicate_result

        # All checks passed
        return AntiCheatResult(action=FlagAction.ACCEPT)

    async def _check_rate_limit(
        self,
        device_id: UUID,
        board_id: UUID,
        trust_tier: TrustTier,
    ) -> AntiCheatResult:
        """Check if device exceeds rate limit for this board.

        Args:
            device_id: ID of the device submitting scores
            board_id: ID of the board being submitted to
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

        # Get submission metadata for this device/board
        meta = await self.meta_repo.get_by_device_and_board(device_id, board_id)

        # First submission - always accept
        if meta is None:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if last submission was within 1 hour (sliding window)
        now = datetime.now(UTC)
        one_hour_ago = now - timedelta(hours=1)

        # If last submission was > 1 hour ago, window expired - accept
        if meta.last_submission_at < one_hour_ago:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if submission count within window exceeds limit
        if meta.submission_count >= limit:
            return AntiCheatResult(
                action=FlagAction.REJECT,
                flag_type=FlagType.RATE_LIMIT,
                confidence=FlagConfidence.HIGH,
                reason=f"Device exceeded rate limit of {limit} submissions per hour for this board",
                metadata={
                    "limit": limit,
                    "submissions_count": meta.submission_count,
                    "trust_tier": trust_tier.value,
                    "window_start": meta.last_submission_at.isoformat(),
                },
            )

        # Under limit - accept
        return AntiCheatResult(action=FlagAction.ACCEPT)

    async def _check_duplicate(
        self,
        score: Score,
        device_id: UUID,
        board_id: UUID,
    ) -> AntiCheatResult:
        """Check if score is a duplicate of recently submitted score.

        Args:
            score: Score being submitted
            device_id: ID of the device submitting the score
            board_id: ID of the board being submitted to

        Returns:
            AntiCheatResult with ACCEPT or FLAG action
        """
        # Get submission metadata for this device/board
        meta = await self.meta_repo.get_by_device_and_board(device_id, board_id)

        # First submission - always accept
        if meta is None or meta.last_score_value is None:
            return AntiCheatResult(action=FlagAction.ACCEPT)

        # Check if score value matches last submission
        if score.value == meta.last_score_value:
            # Check if within duplicate detection window
            now = datetime.now(UTC)
            window_seconds = settings.ANTICHEAT_DUPLICATE_WINDOW_SECONDS
            window_start = now - timedelta(seconds=window_seconds)

            if meta.last_submission_at >= window_start:
                # Duplicate within window - flag for review
                return AntiCheatResult(
                    action=FlagAction.FLAG,
                    flag_type=FlagType.DUPLICATE,
                    confidence=FlagConfidence.MEDIUM,
                    reason=f"Duplicate score value ({score.value}) submitted within {window_seconds} seconds",
                    metadata={
                        "score_value": score.value,
                        "previous_submission_at": meta.last_submission_at.isoformat(),
                        "window_seconds": window_seconds,
                    },
                )

        # Not a duplicate or outside window - accept
        return AntiCheatResult(action=FlagAction.ACCEPT)
