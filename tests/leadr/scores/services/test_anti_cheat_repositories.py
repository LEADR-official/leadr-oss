"""Tests for anti-cheat repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import BoardID, IdentityID, ScoreEventID, ScoreFlagID, UserID
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)


@pytest.mark.asyncio
class TestScoreSubmissionMetaRepository:
    """Test suite for ScoreSubmissionMeta repository."""

    async def test_create_submission_meta(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test creating a submission meta via repository."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )

        created = await repo.create(meta)

        assert created.id == meta.id
        assert created.score_event_id == ScoreEventID(score_event_orm.id)
        assert created.identity_id == IdentityID(identity_orm.id)
        assert created.board_id == BoardID(score_event_orm.board_id)
        assert created.submission_count == 1
        assert created.last_submission_at == now

    async def test_get_submission_meta_by_id(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test retrieving a submission meta by ID."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=5,
            last_submission_at=now,
        )
        await repo.create(meta)

        retrieved = await repo.get_by_id(meta.id)

        assert retrieved is not None
        assert retrieved.id == meta.id
        assert retrieved.submission_count == 5

    async def test_get_submission_meta_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent submission meta returns None."""
        repo = ScoreSubmissionMetaRepository(db_session)
        from leadr.common.domain.ids import ScoreSubmissionMetaID

        non_existent_id = ScoreSubmissionMetaID(uuid4())

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_submission_meta(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test updating a submission meta."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        # Update it
        new_time = datetime.now(UTC)
        meta.submission_count = 10
        meta.last_submission_at = new_time
        updated = await repo.update(meta)

        assert updated.submission_count == 10
        assert updated.last_submission_at == new_time

    async def test_get_by_identity_and_board(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test retrieving submission meta by identity and board IDs."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        board_id = BoardID(score_event_orm.board_id)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=board_id,
            submission_count=3,
            last_submission_at=now,
        )
        await repo.create(meta)

        retrieved = await repo.get_by_identity_and_board(IdentityID(identity_orm.id), board_id)

        assert retrieved is not None
        assert retrieved.identity_id == IdentityID(identity_orm.id)
        assert retrieved.board_id == board_id
        assert retrieved.submission_count == 3

    async def test_get_by_identity_and_board_not_found(self, db_session: AsyncSession):
        """Test that get_by_identity_and_board returns None when not found."""
        repo = ScoreSubmissionMetaRepository(db_session)

        result = await repo.get_by_identity_and_board(IdentityID(uuid4()), BoardID(uuid4()))

        assert result is None


@pytest.mark.asyncio
class TestScoreFlagRepository:
    """Test suite for ScoreFlag repository."""

    async def test_create_flag(self, db_session: AsyncSession, score_event_orm):
        """Test creating a flag via repository."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101, "limit": 100},
            status=ScoreFlagStatus.PENDING,
        )

        created = await repo.create(flag)

        assert created.id == flag.id
        assert created.score_event_id == ScoreEventID(score_event_orm.id)
        assert created.flag_type == FlagType.RATE_LIMIT
        assert created.confidence == FlagConfidence.HIGH
        assert created.metadata == {"submissions_count": 101, "limit": 100}
        assert created.status == "pending"

    async def test_get_flag_by_id(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving a flag by ID."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"duplicate_count": 3},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag)

        retrieved = await repo.get_by_id(flag.id)

        assert retrieved is not None
        assert retrieved.id == flag.id
        assert retrieved.flag_type == FlagType.DUPLICATE
        assert retrieved.confidence == FlagConfidence.MEDIUM

    async def test_get_flag_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent flag returns None."""
        repo = ScoreFlagRepository(db_session)
        non_existent_id = ScoreFlagID(uuid4())

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_flag(self, db_session: AsyncSession, score_event_orm):
        """Test updating a flag."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"time_delta_seconds": 0.5},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag)

        # Update it
        reviewed_at = datetime.now(UTC)
        reviewer_id = UserID(uuid4())
        flag.status = ScoreFlagStatus.FALSE_POSITIVE
        flag.reviewed_at = reviewed_at
        flag.reviewer_id = reviewer_id  # type: ignore[misc]
        flag.reviewer_decision = "Legitimate speed"
        updated = await repo.update(flag)

        assert updated.status == "false_positive"
        assert updated.reviewed_at == reviewed_at
        assert updated.reviewer_id == reviewer_id
        assert updated.reviewer_decision == "Legitimate speed"

    async def test_get_flags_by_score_event_id(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving all flags for a score event."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create multiple flags for the same score event
        flag1 = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"count": 100},
        )
        flag2 = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"dup": True},
        )

        await repo.create(flag1)
        await repo.create(flag2)

        # Retrieve all flags for this score event
        flags = await repo.get_flags_by_score_event_id(score_event_id)

        assert len(flags) == 2
        flag_types = {f.flag_type for f in flags}
        assert FlagType.RATE_LIMIT in flag_types
        assert FlagType.DUPLICATE in flag_types

    async def test_get_pending_flags(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving only pending flags."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create flags with different statuses
        pending_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            status=ScoreFlagStatus.PENDING,
        )
        reviewed_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        await repo.create(pending_flag)
        await repo.create(reviewed_flag)

        # Retrieve pending flags
        pending_flags = await repo.get_pending_flags()

        # Should only return pending flags
        assert len(pending_flags) >= 1
        assert all(f.status == "pending" for f in pending_flags)
        assert any(f.id == pending_flag.id for f in pending_flags)
