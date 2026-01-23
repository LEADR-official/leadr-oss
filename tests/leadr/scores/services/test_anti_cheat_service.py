"""Tests for AntiCheatService."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import BoardID, IdentityID, ScoreEventID
from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType, TrustTier
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository
from leadr.scores.services.anti_cheat_service import AntiCheatService


@pytest.fixture
def score_event_domain(score_event_orm) -> ScoreEvent:
    """Create a domain ScoreEvent from the ORM fixture."""
    from leadr.common.domain.ids import AccountID, GameID

    return ScoreEvent(
        id=ScoreEventID(score_event_orm.id),
        account_id=AccountID(score_event_orm.account_id),
        game_id=GameID(score_event_orm.game_id),
        board_id=BoardID(score_event_orm.board_id),
        identity_id=IdentityID(score_event_orm.identity_id),
        event_payload=score_event_orm.event_payload,
        is_test=score_event_orm.is_test,
        timezone=score_event_orm.timezone,
        country=score_event_orm.country,
        city=score_event_orm.city,
    )


@pytest.mark.asyncio
class TestAntiCheatServiceRateLimiting:
    """Test suite for rate limiting detection."""

    async def test_rate_limit_tier_a_under_limit(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that Tier A submissions under 100/hour are accepted."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        # Create submission metadata showing 99 submissions in the last hour
        now = datetime.now(UTC)
        identity_id = IdentityID(identity_orm.id)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        # Check should pass
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.flag_type is None
        assert result.confidence is None

    async def test_rate_limit_tier_a_at_limit(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that Tier A 100th submission is accepted but 101st is rejected."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        identity_id = IdentityID(identity_orm.id)

        # Test at limit (100th submission) - should accept
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=99,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT

        # Update to 100 submissions
        meta.submission_count = 100
        meta.last_submission_at = now - timedelta(minutes=15)
        await meta_repo.update(meta)

        # 101st submission should be rejected
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
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
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that Tier B enforces 50 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        identity_id = IdentityID(identity_orm.id)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=50,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.B,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.metadata is not None
        assert result.metadata["limit"] == 50

    async def test_rate_limit_tier_c_limit(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that Tier C enforces 20 submissions/hour limit."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        now = datetime.now(UTC)
        identity_id = IdentityID(identity_orm.id)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=20,
            last_submission_at=now - timedelta(minutes=30),
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.C,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.REJECT
        assert result.flag_type == FlagType.RATE_LIMIT
        assert result.metadata is not None
        assert result.metadata["limit"] == 20

    async def test_rate_limit_per_board_isolation(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that rate limits are tracked per board (no cross-board contamination)."""
        service = AntiCheatService(db_session)

        # No previous submissions for this board
        identity_id = IdentityID(identity_orm.id)

        # First submission should always pass
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_sliding_window(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that rate limits use a sliding window (old submissions don't count)."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)
        # Old submission from 2 hours ago (outside window)
        old_time = datetime.now(UTC) - timedelta(hours=2)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=200,
            last_submission_at=old_time,
        )
        await meta_repo.create(meta)

        # Should pass because old submissions are outside the window
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_rate_limit_no_previous_submissions(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that first submission (no metadata) is accepted."""
        service = AntiCheatService(db_session)
        identity_id = IdentityID(identity_orm.id)

        # No submission metadata exists
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT


@pytest.mark.asyncio
class TestAntiCheatServiceDuplicateDetection:
    """Test suite for duplicate score detection."""

    async def test_duplicate_within_window_flagged(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that identical values within the duplicate window are flagged."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)
        now = datetime.now(UTC)

        # Create metadata with recent submission of same value
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=5,
            last_submission_at=now - timedelta(seconds=30),
            last_score_value=score_event_domain.event_payload.get("value"),
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.DUPLICATE
        # Duplicate detection uses MEDIUM confidence
        assert result.confidence == FlagConfidence.MEDIUM

    async def test_duplicate_outside_window_accepted(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that identical values outside the duplicate window are accepted."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)

        # Create metadata with old submission of same value
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=5,
            last_submission_at=datetime.now(UTC) - timedelta(minutes=10),
            last_score_value=score_event_domain.event_payload.get("value"),
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_different_score_not_flagged(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that different score values are not flagged as duplicates."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)
        now = datetime.now(UTC)

        # Create metadata with recent submission of different value
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=5,
            last_submission_at=now - timedelta(seconds=30),
            last_score_value=99999.0,  # Different value
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT


@pytest.mark.asyncio
class TestAntiCheatServiceVelocityDetection:
    """Test suite for velocity (rapid submission) detection."""

    async def test_rapid_submission_flagged(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that submissions faster than minimum interval are flagged."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)
        # Submission just 0.5 seconds ago
        recent_time = datetime.now(UTC) - timedelta(milliseconds=500)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=5,
            last_submission_at=recent_time,
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.FLAG
        assert result.flag_type == FlagType.VELOCITY
        assert result.confidence == FlagConfidence.HIGH
        assert result.metadata is not None
        assert "time_since_last_submission" in result.metadata

    async def test_normal_pace_accepted(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that submissions at normal pace are accepted."""
        service = AntiCheatService(db_session)
        meta_repo = ScoreSubmissionMetaRepository(db_session)

        identity_id = IdentityID(identity_orm.id)
        # Submission 5 seconds ago (normal pace)
        normal_time = datetime.now(UTC) - timedelta(seconds=5)
        meta = ScoreSubmissionMeta(
            score_event_id=score_event_domain.id,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
            submission_count=5,
            last_submission_at=normal_time,
            last_score_value=99999.0,  # Different value to avoid duplicate flag
        )
        await meta_repo.create(meta)

        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT

    async def test_first_submission_velocity_check_accepted(
        self, db_session: AsyncSession, score_event_domain: ScoreEvent, identity_orm
    ):
        """Test that first submission (no previous timestamp) is accepted."""
        service = AntiCheatService(db_session)
        identity_id = IdentityID(identity_orm.id)

        # No previous submission metadata
        result = await service.check_submission_for_event(
            score_event=score_event_domain,
            trust_tier=TrustTier.A,
            identity_id=identity_id,
            board_id=score_event_domain.board_id,
        )

        assert result.action == FlagAction.ACCEPT
