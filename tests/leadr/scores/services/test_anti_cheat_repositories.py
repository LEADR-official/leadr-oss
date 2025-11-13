"""Tests for anti-cheat repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)


@pytest.mark.asyncio
class TestScoreSubmissionMetaRepository:
    """Test suite for ScoreSubmissionMeta repository."""

    async def test_create_submission_meta(self, db_session: AsyncSession, test_score):
        """Test creating a submission meta via repository."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        device_id = uuid4()

        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_score.board_id,
            submission_count=1,
            last_submission_at=now,
        )

        created = await repo.create(meta)

        assert created.id == meta.id
        assert created.score_id == test_score.id
        assert created.device_id == device_id
        assert created.board_id == test_score.board_id
        assert created.submission_count == 1
        assert created.last_submission_at == now

    async def test_get_submission_meta_by_id(self, db_session: AsyncSession, test_score):
        """Test retrieving a submission meta by ID."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        device_id = uuid4()

        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_score.board_id,
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
        non_existent_id = uuid4()

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_submission_meta(self, db_session: AsyncSession, test_score):
        """Test updating a submission meta."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        device_id = uuid4()

        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_score.board_id,
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

    async def test_get_by_device_and_board(self, db_session: AsyncSession, test_score, test_board):
        """Test retrieving submission meta by device and board IDs."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        device_id = uuid4()

        meta = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_board.id,
            submission_count=3,
            last_submission_at=now,
        )
        await repo.create(meta)

        retrieved = await repo.get_by_device_and_board(device_id, test_board.id)

        assert retrieved is not None
        assert retrieved.device_id == device_id
        assert retrieved.board_id == test_board.id
        assert retrieved.submission_count == 3

    async def test_get_by_device_and_board_not_found(self, db_session: AsyncSession):
        """Test that get_by_device_and_board returns None when not found."""
        repo = ScoreSubmissionMetaRepository(db_session)

        result = await repo.get_by_device_and_board(uuid4(), uuid4())

        assert result is None


@pytest.mark.asyncio
class TestScoreFlagRepository:
    """Test suite for ScoreFlag repository."""

    async def test_create_flag(self, db_session: AsyncSession, test_score):
        """Test creating a flag via repository."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101, "limit": 100},
            status=ScoreFlagStatus.PENDING,
        )

        created = await repo.create(flag)

        assert created.id == flag.id
        assert created.score_id == test_score.id
        assert created.flag_type == FlagType.RATE_LIMIT
        assert created.confidence == FlagConfidence.HIGH
        assert created.metadata == {"submissions_count": 101, "limit": 100}
        assert created.status == "PENDING"

    async def test_get_flag_by_id(self, db_session: AsyncSession, test_score):
        """Test retrieving a flag by ID."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_id=test_score.id,
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
        non_existent_id = uuid4()

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_flag(self, db_session: AsyncSession, test_score):
        """Test updating a flag."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"time_delta_seconds": 0.5},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag)

        # Update it
        reviewed_at = datetime.now(UTC)
        reviewer_id = uuid4()
        flag.status = ScoreFlagStatus.FALSE_POSITIVE
        flag.reviewed_at = reviewed_at
        flag.reviewer_id = reviewer_id
        flag.reviewer_decision = "Legitimate speed"
        updated = await repo.update(flag)

        assert updated.status == "FALSE_POSITIVE"
        assert updated.reviewed_at == reviewed_at
        assert updated.reviewer_id == reviewer_id
        assert updated.reviewer_decision == "Legitimate speed"

    async def test_get_flags_by_score_id(self, db_session: AsyncSession, test_score):
        """Test retrieving all flags for a score."""
        repo = ScoreFlagRepository(db_session)

        # Create multiple flags for the same score
        flag1 = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101},
        )
        await repo.create(flag1)

        flag2 = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"duplicate_count": 2},
        )
        await repo.create(flag2)

        flags = await repo.get_flags_by_score_id(test_score.id)

        assert len(flags) == 2
        flag_types = {f.flag_type for f in flags}
        assert FlagType.RATE_LIMIT in flag_types
        assert FlagType.DUPLICATE in flag_types

    async def test_get_pending_flags(self, db_session: AsyncSession, test_score):
        """Test retrieving only pending flags."""
        repo = ScoreFlagRepository(db_session)

        # Create pending flag
        flag1 = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag1)

        # Create reviewed flag
        flag2 = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"duplicate_count": 2},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )
        await repo.create(flag2)

        pending = await repo.get_pending_flags()

        assert len(pending) == 1
        assert pending[0].status == "PENDING"
        assert pending[0].flag_type == FlagType.RATE_LIMIT
