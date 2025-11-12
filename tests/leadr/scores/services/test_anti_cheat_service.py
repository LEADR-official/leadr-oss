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
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that Tier A submissions under 100/hour are accepted."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        # Create submission metadata showing 99 submissions in the last hour
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            user_id=test_user.id,
            board_id=test_board.id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # Check should pass
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
        assert result.confidence is None

    async def test_rate_limit_tier_a_at_limit(
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that Tier A 100th submission is accepted but 101st is rejected."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)

        # Test at limit (100th submission) - should accept
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            user_id=test_user.id,
            board_id=test_board.id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            user_id=test_user.id,
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
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert "rate limit" in result.reason.lower()
        assert result.metadata["limit"] == 100
        assert result.metadata["submissions_count"] == 100

    async def test_rate_limit_tier_b_limit(
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that Tier B enforces 50 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            user_id=test_user.id,
            board_id=test_board.id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # 51st submission should be rejected
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata["limit"] == 50

    async def test_rate_limit_tier_c_limit(
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that Tier C enforces 20 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            user_id=test_user.id,
            board_id=test_board.id,
            submission_count=20,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # 21st submission should be rejected
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.C,
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata["limit"] == 20

    async def test_rate_limit_per_board_isolation(
        self, db_session: AsyncSession, test_score: Score, test_user, test_account, test_game
    ):
        """Test that rate limits are per-board (submissions to different boards don't interfere)."""
        from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
        from leadr.boards.services.repositories import BoardRepository

        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        # Create two boards
        board_repo = BoardRepository(db_session)
        now = datetime.now(UTC)

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
            user_id=test_user.id,
            board_id=board1.id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta1)

        # Submission to board1 should be rejected (over limit)
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            user_id=test_user.id,
            board_id=board1.id,
        )
        assert result.action == FlagAction.REJECT

        # Submission to board2 should be accepted (no submissions yet)
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.B,
            user_id=test_user.id,
            board_id=board2.id,
        )
        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_sliding_window(
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that submissions older than 1 hour don't count toward limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)

        # Create metadata with last submission 61 minutes ago (outside window)
        # Even though count is 100, it's outside the 1-hour window
        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            user_id=test_user.id,
            board_id=test_board.id,
            submission_count=100,
            last_submission_at=now - timedelta(minutes=61),
        )
        await meta_repo.create(meta)

        # Should accept because the sliding window has expired
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.A,
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_no_previous_submissions(
        self, db_session: AsyncSession, test_score: Score, test_user, test_board
    ):
        """Test that first submission is always accepted."""
        service = AntiCheatService(db_session)

        # No metadata exists - first submission
        result = await service.check_submission(
            score=test_score,
            trust_tier=TrustTier.C,  # Even for strictest tier
            user_id=test_user.id,
            board_id=test_board.id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
