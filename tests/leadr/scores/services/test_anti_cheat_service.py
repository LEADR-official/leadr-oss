"""Tests for AntiCheatService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreEventID
from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType, TrustTier
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.anti_cheat_service import AntiCheatService


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def service(mock_session):
    """Create AntiCheatService with mocked repository."""
    svc = AntiCheatService(mock_session)
    svc.meta_repo = MagicMock()
    return svc


@pytest.fixture
def score_event() -> ScoreEvent:
    """Create a domain ScoreEvent for testing."""
    return ScoreEvent(
        id=ScoreEventID(uuid4()),
        account_id=AccountID(uuid4()),
        game_id=GameID(uuid4()),
        board_id=BoardID(uuid4()),
        identity_id=IdentityID(uuid4()),
        event_payload={"value": 1000.0},
        is_test=False,
        timezone="UTC",
        country="US",
        city="New York",
    )


@pytest.fixture
def identity_id() -> IdentityID:
    """Create an identity ID for testing."""
    return IdentityID(uuid4())


@pytest.mark.asyncio
class TestAntiCheatServiceRateLimiting:
    """Test suite for rate limiting detection."""

    async def test_rate_limit_tier_a_under_limit(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that Tier A submissions under 100/hour are accepted."""
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
        assert result.confidence is None

    async def test_rate_limit_tier_a_at_limit(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that Tier A 100th submission is accepted but 101st is rejected."""
        now = datetime.now(UTC)

        # Test at limit (100th submission) - should accept
        meta_at_99 = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta_at_99)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT

        # Update to 100 submissions - 101st should be rejected
        meta_at_100 = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=100,
            last_submission_at=now - timedelta(minutes=15),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta_at_100)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.confidence == FlagConfidence.HIGH
        assert result.reason is not None
        assert "rate limit" in result.reason.lower()
        assert result.metadata is not None
        assert result.metadata["limit"] == 100
        assert result.metadata["submissions_count"] == 100

    async def test_rate_limit_tier_b_limit(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that Tier B enforces 50 submissions/hour limit."""
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.B,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.metadata is not None
        assert result.metadata["limit"] == 50

    async def test_rate_limit_tier_c_limit(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that Tier C enforces 20 submissions/hour limit."""
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=20,
            last_submission_at=now - timedelta(minutes=30),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.C,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.metadata is not None
        assert result.metadata["limit"] == 20

    async def test_rate_limit_per_board_isolation(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that rate limits are tracked per board (no cross-board contamination)."""
        # No previous submissions for this board
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=None)

        # First submission should always pass
        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_sliding_window(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that rate limits use a sliding window (old submissions don't count)."""
        # Old submission from 2 hours ago (outside window)
        old_time = datetime.now(UTC) - timedelta(hours=2)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=200,
            last_submission_at=old_time,
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        # Should pass because old submissions are outside the window
        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_no_previous_submissions(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that first submission (no metadata) is accepted."""
        # No submission metadata exists
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=None)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT


@pytest.mark.asyncio
class TestAntiCheatServiceDuplicateDetection:
    """Test suite for duplicate score detection."""

    async def test_duplicate_within_window_flagged(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that identical values within the duplicate window are flagged."""
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=5,
            last_submission_at=now - timedelta(seconds=30),
            last_score_value=score_event.event_payload.get("value"),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.DUPLICATE
        # Duplicate detection uses MEDIUM confidence
        assert result.confidence == FlagConfidence.MEDIUM

    async def test_duplicate_outside_window_accepted(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that identical values outside the duplicate window are accepted."""
        # Create metadata with old submission of same value
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=5,
            last_submission_at=datetime.now(UTC) - timedelta(minutes=10),
            last_score_value=score_event.event_payload.get("value"),
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_different_score_not_flagged(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that different score values are not flagged as duplicates."""
        now = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=5,
            last_submission_at=now - timedelta(seconds=30),
            last_score_value=99999.0,  # Different value
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT


@pytest.mark.asyncio
class TestAntiCheatServiceVelocityDetection:
    """Test suite for velocity (rapid submission) detection."""

    async def test_rapid_submission_flagged(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that submissions faster than minimum interval are flagged."""
        # Submission just 0.5 seconds ago
        recent_time = datetime.now(UTC) - timedelta(milliseconds=500)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=5,
            last_submission_at=recent_time,
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.VELOCITY
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata is not None
        assert "time_since_last_submission" in result.metadata

    async def test_normal_pace_accepted(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that submissions at normal pace are accepted."""
        # Submission 5 seconds ago (normal pace)
        normal_time = datetime.now(UTC) - timedelta(seconds=5)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event.id,
            identity_id=identity_id,
            board_id=score_event.board_id,
            submission_count=5,
            last_submission_at=normal_time,
            last_score_value=99999.0,  # Different value to avoid duplicate flag
        )
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=meta)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_first_submission_velocity_check_accepted(
        self, service: AntiCheatService, score_event: ScoreEvent, identity_id: IdentityID
    ):
        """Test that first submission (no previous timestamp) is accepted."""
        # No previous submission metadata
        service.meta_repo.get_by_identity_and_board = AsyncMock(return_value=None)

        result = await service.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event.board_id,
        )

        assert result.action == FlagAction.ACCEPT
