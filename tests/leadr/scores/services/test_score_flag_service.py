"""Tests for ScoreFlagService."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import ScoreEventID, ScoreFlagID
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.score_flag_service import ScoreFlagService


@pytest.mark.asyncio
class TestScoreFlagService:
    """Test suite for ScoreFlagService."""

    async def test_get_flag(self, db_session: AsyncSession, score_event_orm):
        """Test getting a flag by ID."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Get the flag using get_flag method
        retrieved_flag = await service.get_flag(created_flag.id)

        assert retrieved_flag is not None
        assert retrieved_flag.id == created_flag.id
        assert retrieved_flag.score_event_id == ScoreEventID(score_event_orm.id)
        assert retrieved_flag.flag_type == FlagType.VELOCITY

    async def test_get_flag_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test get_flag returns None for nonexistent flag."""
        service = ScoreFlagService(db_session)
        flag = await service.get_flag(ScoreFlagID(uuid4()))

        assert flag is None

    async def test_update_flag_with_status_only(self, db_session: AsyncSession, score_event_orm):
        """Test updating a flag with status only."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag status
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        assert updated_flag.status == ScoreFlagStatus.FALSE_POSITIVE
        assert updated_flag.reviewed_at is not None
        assert updated_flag.reviewer_decision is None  # Not provided

    async def test_update_flag_with_reviewer_decision_only(
        self, db_session: AsyncSession, score_event_orm
    ):
        """Test updating a flag with reviewer decision only."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag with only reviewer decision
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            reviewer_decision="Looks suspicious but needs more data",
        )

        assert updated_flag.reviewer_decision == "Looks suspicious but needs more data"
        assert updated_flag.status == ScoreFlagStatus.PENDING  # Unchanged
        assert updated_flag.reviewed_at is None  # Not set when status unchanged

    async def test_update_flag_with_both_status_and_decision(
        self, db_session: AsyncSession, score_event_orm
    ):
        """Test updating a flag with both status and reviewer decision."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag with both status and decision
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified suspicious pattern",
        )

        assert updated_flag.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert updated_flag.reviewer_decision == "Verified suspicious pattern"
        assert updated_flag.reviewed_at is not None
