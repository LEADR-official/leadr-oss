"""Tests for AntiCheatService."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType, TrustTier
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
from leadr.scores.domain.score import Score
from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository
from leadr.scores.services.anti_cheat_service import AntiCheatService


@pytest.mark.asyncio
class TestAntiCheatServiceRateLimiting:
    """Test suite for rate limiting detection."""

    async def test_rate_limit_tier_a_under_limit(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that Tier A submissions under 100/hour are accepted."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        # Create submission metadata showing 99 submissions in the last hour
        now = datetime.now(UTC)
        device_id = uuid4()
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # Check should pass
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
        assert result.confidence is None

    async def test_rate_limit_tier_a_at_limit(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that Tier A 100th submission is accepted but 101st is rejected."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        device_id = uuid4()

        # Test at limit (100th submission) - should accept
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT

        # Update to 100 submissions
        meta.submission_count = 100
        meta.last_submission_at = now - timedelta(minutes=15)
        await meta_repo.update(meta)

        # 101st submission should be rejected
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert "rate limit" in result.reason.lower()
        assert result.metadata["limit"] == 100
        assert result.metadata["submissions_count"] == 100

    async def test_rate_limit_tier_b_limit(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that Tier B enforces 50 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        device_id = uuid4()
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # 51st submission should be rejected
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata["limit"] == 50

    async def test_rate_limit_tier_c_limit(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that Tier C enforces 20 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        device_id = uuid4()
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=20,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # 21st submission should be rejected
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.C,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata["limit"] == 20

    async def test_rate_limit_per_board_isolation(
        self, db_session: AsyncSession, test_score: Score, test_account, test_game
    ):
        """Test that rate limits are per-board (submissions to different boards don't interfere)."""
        from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
        from leadr.boards.services.repositories import BoardRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        # Create two boards
        board_repo = BoardRepository(db_session)
        now = datetime.now(UTC)
        device_id = uuid4()

        board1 = Board(
            id=uuid4(),
            account_id=test_account.id,
            game_id=test_game.id,
            name="Board 1",
            icon="trophy",
            short_code="BOARD1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board1)

        board2 = Board(
            id=uuid4(),
            account_id=test_account.id,
            game_id=test_game.id,
            name="Board 2",
            icon="star",
            short_code="BOARD2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board2)

        # Add 50 submissions to board1 (at Tier B limit)
        meta1 = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=board1.id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta1)

        # Submission to board1 should be rejected (over limit)
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            device_id=device_id,
            board_id=board1.id,
        )
        assert result.action == FlagAction.REJECT

        # Submission to board2 should be accepted (no submissions yet)
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            device_id=device_id,
            board_id=board2.id,
        )
        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_sliding_window(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that submissions older than 1 hour don't count toward limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        device_id = uuid4()

        # Create metadata with last submission 61 minutes ago (outside window)
        # Even though count is 100, it's outside the 1-hour window
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=100,
            last_submission_at=now - timedelta(minutes=61),
        )
        await meta_repo.create(meta)

        # Should accept because the sliding window has expired
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_no_previous_submissions(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that first submission is always accepted."""
        service = AntiCheatService(db_session)
        device_id = uuid4()

        # No metadata exists - first submission
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.C,  # Even for strictest tier
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None


@pytest.mark.asyncio
class TestAntiCheatServiceDuplicateDetection:
    """Test suite for duplicate score detection."""

    async def test_duplicate_within_window_flagged(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that duplicate score within 5 minutes is flagged."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
        from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        device_id = uuid4()
        now = datetime.now(UTC)

        # Create metadata simulating a previous submission with value 1000.0
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=1,
            last_submission_at=now - timedelta(seconds=30),
            last_score_value=1000.0,  # Previous score value
        )
        await meta_repo.create(meta)

        # Submit same score value again (duplicate within window)
        result = await service.check_submission(
            score=test_score,  # Same value 1000.0
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.DUPLICATE
        assert result.confidence == FlagConfidence.MEDIUM
        assert "duplicate" in result.reason.lower()

    async def test_duplicate_outside_window_accepted(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that duplicate score outside 5-minute window is accepted."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
        from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        device_id = uuid4()
        now = datetime.now(UTC)

        # Create metadata with last submission 6 minutes ago (outside window)
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=1,
            last_submission_at=now - timedelta(minutes=6),
            last_score_value=1000.0,  # Previous score value
        )
        await meta_repo.create(meta)

        # Submit same score value - should accept (window expired)
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_different_score_not_flagged(self, db_session: AsyncSession, test_board):
        """Test that different score values are not flagged as duplicates."""
        from leadr.scores.domain.score import Score

        service = AntiCheatService(db_session)
        device_id = uuid4()

        # First score with value 1000.0
        score1 = Score(
            account_id=test_board.account_id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            user_id=uuid4(),
            player_name="Test Player",
            value=1000.0,
        )

        result = await service.check_submission(
            score=score1,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )
        assert result.action == FlagAction.ACCEPT

        # Second score with different value 2000.0
        score2 = Score(
            account_id=test_board.account_id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            user_id=uuid4(),
            player_name="Test Player",
            value=2000.0,
        )

        result = await service.check_submission(
            score=score2,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None


@pytest.mark.asyncio
class TestAntiCheatServiceVelocityDetection:
    """Test suite for velocity detection (rapid-fire submissions)."""

    async def test_rapid_submission_flagged(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that submission within 2 seconds is flagged."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
        from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        device_id = uuid4()
        now = datetime.now(UTC)

        # Create metadata simulating a submission 1 second ago
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=1,
            last_submission_at=now - timedelta(seconds=1),
            last_score_value=500.0,
        )
        await meta_repo.create(meta)

        # Submit again within velocity threshold
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.VELOCITY
        assert result.confidence == FlagConfidence.HIGH
        assert "rapid" in result.reason.lower() or "velocity" in result.reason.lower()

    async def test_normal_pace_accepted(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that submission after 2+ seconds is accepted."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
        from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        device_id = uuid4()
        now = datetime.now(UTC)

        # Create metadata simulating a submission 3 seconds ago (above threshold)
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=1,
            last_submission_at=now - timedelta(seconds=3),
            last_score_value=500.0,
        )
        await meta_repo.create(meta)

        # Submit again after threshold - should accept
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_first_submission_velocity_check_accepted(
        self, db_session: AsyncSession, test_score: Score, test_board
    ):
        """Test that first submission always passes velocity check."""
        service = AntiCheatService(db_session)
        device_id = uuid4()

        # No metadata exists - first submission
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            device_id=device_id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
