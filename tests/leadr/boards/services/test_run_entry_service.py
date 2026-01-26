"""Tests for RunEntryService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID, ScoreEventID
from leadr.common.domain.pagination_result import PaginatedResult


class TestRunEntryService:
    """Test suite for RunEntryService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create a RunEntryService with mocked repository."""
        svc = RunEntryService(mock_session)
        svc.repository = MagicMock()
        return svc

    @pytest.mark.asyncio
    async def test_create_run_entry(self, service):
        """Test creating a run entry."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        score_event_id = ScoreEventID(uuid4())
        now = datetime.now(UTC)

        expected_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=1000.0,
            created_at=now,
            updated_at=now,
        )

        service.repository.create = AsyncMock(return_value=expected_entry)

        result = await service.create_run_entry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=1000.0,
        )

        assert result.board_id == board_id
        assert result.identity_id == identity_id
        assert result.score_event_id == score_event_id
        assert result.primary_value == 1000.0
        service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_run_entry(self, service):
        """Test getting a run entry by ID."""
        entry_id = RunEntryID(uuid4())
        expected_entry = RunEntry(
            id=entry_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=500.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_entry)

        result = await service.get_run_entry(entry_id)

        assert result == expected_entry
        service.repository.get_by_id.assert_called_once_with(entry_id)

    @pytest.mark.asyncio
    async def test_get_run_entry_not_found(self, service):
        """Test getting a non-existent run entry returns None."""
        entry_id = RunEntryID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_run_entry(entry_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_success(self, service):
        """Test get_by_id_or_raise returns entry when found."""
        entry_id = RunEntryID(uuid4())
        expected_entry = RunEntry(
            id=entry_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=500.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_entry)

        result = await service.get_by_id_or_raise(entry_id)

        assert result == expected_entry

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_not_found(self, service):
        """Test get_by_id_or_raise raises when not found."""
        entry_id = RunEntryID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.get_by_id_or_raise(entry_id)

        assert "RunEntry" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_board_and_score_event(self, service):
        """Test getting a run entry by board and score event."""
        board_id = BoardID(uuid4())
        score_event_id = ScoreEventID(uuid4())
        expected_entry = RunEntry(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            score_event_id=score_event_id,
            primary_value=750.0,
        )

        service.repository.get_by_board_and_score_event = AsyncMock(return_value=expected_entry)

        result = await service.get_by_board_and_score_event(board_id, score_event_id)

        assert result == expected_entry
        service.repository.get_by_board_and_score_event.assert_called_once_with(
            board_id, score_event_id
        )

    @pytest.mark.asyncio
    async def test_list_run_entries(self, service):
        """Test listing run entries."""
        board_id = BoardID(uuid4())

        entry1 = RunEntry(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=100.0,
        )
        entry2 = RunEntry(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=200.0,
        )

        mock_result = PaginatedResult(
            items=[entry1, entry2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await service.list_run_entries(board_id=board_id, pagination=pagination)

        assert len(result.items) == 2
        assert result.has_next is False

    @pytest.mark.asyncio
    async def test_soft_delete_run_entry(self, service):
        """Test soft deleting a run entry."""
        entry_id = RunEntryID(uuid4())
        existing_entry = RunEntry(
            id=entry_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=100.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=existing_entry)
        service.repository.update = AsyncMock(return_value=existing_entry)

        result = await service.soft_delete(entry_id)

        assert result.is_deleted is True
        service.repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, service):
        """Test soft delete raises when entry not found."""
        entry_id = RunEntryID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.soft_delete(entry_id)

    @pytest.mark.asyncio
    async def test_list_run_entries_with_is_test_filter(self, service):
        """Test listing run entries with is_test filter."""
        board_id = BoardID(uuid4())

        entry1 = RunEntry(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=100.0,
            is_test=True,
        )

        mock_result = PaginatedResult(
            items=[entry1],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await service.list_run_entries(
            board_id=board_id,
            is_test=True,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is True
        # Verify is_test was passed to repository
        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args.kwargs
        assert call_kwargs.get("is_test") is True
