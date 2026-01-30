"""Tests for ScoreFlagService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import ScoreEventID, ScoreFlagID, UserID
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.score_flag_service import ScoreFlagService


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    """Create service with mocked repository."""
    svc = ScoreFlagService(mock_session)
    svc.repository = MagicMock()
    return svc


@pytest.mark.asyncio
class TestScoreFlagService:
    """Test suite for ScoreFlagService."""

    async def test_get_flag(self, service):
        """Test getting a flag by ID."""
        flag_id = ScoreFlagID()
        expected_flag = ScoreFlag(
            score_event_id=ScoreEventID(),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        service.repository.get_by_id = AsyncMock(return_value=expected_flag)

        result = await service.get_flag(flag_id)

        assert result is not None
        assert result.id == flag_id
        assert result.flag_type == FlagType.VELOCITY
        service.repository.get_by_id.assert_awaited_once_with(flag_id)

    async def test_get_flag_returns_none_for_nonexistent(self, service):
        """Test get_flag returns None for nonexistent flag."""
        flag_id = ScoreFlagID(uuid4())
        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_flag(flag_id)

        assert result is None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)

    async def test_update_flag_with_status_only(self, service):
        """Test updating a flag with status only."""
        flag_id = ScoreFlagID()
        score_event_id = ScoreEventID()

        original_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=original_flag)

        updated_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewed_at=datetime.now(UTC),
        ).model_copy(update={"id": flag_id})

        service.repository.update = AsyncMock(return_value=updated_flag)

        # Mock _sync_ranking_status to avoid dealing with complex dependencies
        service._sync_ranking_status = AsyncMock()

        # Execute
        result = await service.update_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        assert result.status == ScoreFlagStatus.FALSE_POSITIVE
        assert result.reviewed_at is not None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)
        service.repository.update.assert_awaited_once()
        service._sync_ranking_status.assert_awaited_once()

    async def test_update_flag_with_reviewer_decision_only(self, service):
        """Test updating a flag with reviewer decision only."""
        flag_id = ScoreFlagID()
        score_event_id = ScoreEventID()

        original_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        service.repository.get_by_id = AsyncMock(return_value=original_flag)

        updated_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
            reviewer_decision="Looks suspicious but needs more data",
        ).model_copy(update={"id": flag_id})

        service.repository.update = AsyncMock(return_value=updated_flag)

        result = await service.update_flag(
            flag_id=flag_id,
            reviewer_decision="Looks suspicious but needs more data",
        )

        assert result.reviewer_decision == "Looks suspicious but needs more data"
        assert result.status == ScoreFlagStatus.PENDING
        assert result.reviewed_at is None  # Not set when status unchanged
        service.repository.get_by_id.assert_awaited_once_with(flag_id)
        service.repository.update.assert_awaited_once()

    async def test_update_flag_with_both_status_and_decision(self, service):
        """Test updating a flag with both status and reviewer decision."""
        flag_id = ScoreFlagID()
        score_event_id = ScoreEventID()

        original_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        service.repository.get_by_id = AsyncMock(return_value=original_flag)

        updated_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified suspicious pattern",
            reviewed_at=datetime.now(UTC),
        ).model_copy(update={"id": flag_id})

        service.repository.update = AsyncMock(return_value=updated_flag)

        # Mock _sync_ranking_status to avoid dealing with complex dependencies
        service._sync_ranking_status = AsyncMock()

        result = await service.update_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified suspicious pattern",
        )

        assert result.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert result.reviewer_decision == "Verified suspicious pattern"
        assert result.reviewed_at is not None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)
        service.repository.update.assert_awaited_once()
        service._sync_ranking_status.assert_awaited_once()


@pytest.mark.asyncio
class TestReviewFlag:
    """Test the review_flag method."""

    async def test_review_flag_confirms_cheat(self, service):
        """Test review_flag method with confirmed cheat status."""
        flag_id = ScoreFlagID()
        score_event_id = ScoreEventID()
        reviewer_id = UserID()

        original_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        service.repository.get_by_id = AsyncMock(return_value=original_flag)

        updated_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified cheating",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(UTC),
        ).model_copy(update={"id": flag_id})

        service.repository.update = AsyncMock(return_value=updated_flag)

        # Mock _sync_ranking_status to avoid dealing with complex dependencies
        service._sync_ranking_status = AsyncMock()

        result = await service.review_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified cheating",
            reviewer_id=reviewer_id,
        )

        assert result.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert result.reviewer_decision == "Verified cheating"
        assert result.reviewer_id == reviewer_id
        assert result.reviewed_at is not None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)
        service.repository.update.assert_awaited_once()
        service._sync_ranking_status.assert_awaited_once()

    async def test_review_flag_false_positive(self, service):
        """Test review_flag method with false positive status."""
        flag_id = ScoreFlagID()
        score_event_id = ScoreEventID()

        original_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        ).model_copy(update={"id": flag_id})

        service.repository.get_by_id = AsyncMock(return_value=original_flag)

        updated_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewer_decision="Legitimate gameplay",
            reviewed_at=datetime.now(UTC),
        ).model_copy(update={"id": flag_id})

        service.repository.update = AsyncMock(return_value=updated_flag)

        # Mock _sync_ranking_status to avoid dealing with complex dependencies
        service._sync_ranking_status = AsyncMock()

        result = await service.review_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewer_decision="Legitimate gameplay",
        )

        assert result.status == ScoreFlagStatus.FALSE_POSITIVE
        assert result.reviewer_decision == "Legitimate gameplay"
        assert result.reviewed_at is not None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)
        service.repository.update.assert_awaited_once()
        service._sync_ranking_status.assert_awaited_once()

    async def test_review_flag_not_found(self, service):
        """Test review_flag raises error for non-existent flag."""
        flag_id = ScoreFlagID()

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.review_flag(
                flag_id=flag_id,
                status=ScoreFlagStatus.CONFIRMED_CHEAT,
            )

        service.repository.get_by_id.assert_awaited_once_with(flag_id)
