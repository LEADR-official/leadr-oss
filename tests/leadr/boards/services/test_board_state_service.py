"""Tests for BoardStateService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.board_state_service import BoardStateService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID
from leadr.common.domain.pagination_result import PaginatedResult


class TestBoardStateService:
    """Test suite for BoardStateService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create a BoardStateService with mocked repository."""
        svc = BoardStateService(mock_session)
        svc.repository = MagicMock()
        return svc

    @pytest.mark.asyncio
    async def test_create_board_state(self, service):
        """Test creating a board state."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        expected_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.0,
            aux={"event_count": 1},
            created_at=now,
            updated_at=now,
        )

        service.repository.create = AsyncMock(return_value=expected_state)

        result = await service.create_board_state(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.0,
            aux={"event_count": 1},
        )

        assert result.board_id == board_id
        assert result.identity_id == identity_id
        assert result.primary_value == 1000.0
        assert result.aux == {"event_count": 1}
        service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_board_state(self, service):
        """Test getting a board state by ID."""
        state_id = BoardStateID(uuid4())
        expected_state = BoardState(
            id=state_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            primary_value=500.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_state)

        result = await service.get_board_state(state_id)

        assert result == expected_state
        service.repository.get_by_id.assert_called_once_with(state_id)

    @pytest.mark.asyncio
    async def test_get_board_state_not_found(self, service):
        """Test getting a non-existent board state returns None."""
        state_id = BoardStateID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_board_state(state_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_success(self, service):
        """Test get_by_id_or_raise returns state when found."""
        state_id = BoardStateID(uuid4())
        expected_state = BoardState(
            id=state_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            primary_value=500.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_state)

        result = await service.get_by_id_or_raise(state_id)

        assert result == expected_state

    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_not_found(self, service):
        """Test get_by_id_or_raise raises when not found."""
        state_id = BoardStateID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.get_by_id_or_raise(state_id)

        assert "BoardState" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_board_and_identity(self, service):
        """Test getting a board state by board and identity."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        expected_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=750.0,
        )

        service.repository.get_by_board_and_identity = AsyncMock(return_value=expected_state)

        result = await service.get_by_board_and_identity(board_id, identity_id)

        assert result == expected_state
        service.repository.get_by_board_and_identity.assert_called_once_with(board_id, identity_id)

    @pytest.mark.asyncio
    async def test_upsert_board_state_create_new(self, service):
        """Test upsert creates new state when none exists."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        # No existing state
        service.repository.get_by_board_and_identity = AsyncMock(return_value=None)

        expected_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )
        service.repository.create = AsyncMock(return_value=expected_state)

        result = await service.upsert_board_state(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        assert result.primary_value == 100.0
        service.repository.create.assert_called_once()
        service.repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_board_state_update_existing(self, service):
        """Test upsert updates existing state."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        existing_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            aux={"old": "data"},
        )
        service.repository.get_by_board_and_identity = AsyncMock(return_value=existing_state)

        updated_state = BoardState(
            id=existing_state.id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=200.0,
            aux={"new": "data"},
        )
        service.repository.update = AsyncMock(return_value=updated_state)

        result = await service.upsert_board_state(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=200.0,
            aux={"new": "data"},
        )

        assert result.primary_value == 200.0
        assert result.aux == {"new": "data"}
        service.repository.update.assert_called_once()
        service.repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_board_states(self, service):
        """Test listing board states."""
        board_id = BoardID(uuid4())

        state1 = BoardState(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            primary_value=100.0,
        )
        state2 = BoardState(
            board_id=board_id,
            identity_id=IdentityID(uuid4()),
            primary_value=200.0,
        )

        mock_result = PaginatedResult(
            items=[state1, state2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await service.list_board_states(board_id=board_id, pagination=pagination)

        assert len(result.items) == 2
        assert result.has_next is False

    @pytest.mark.asyncio
    async def test_soft_delete_board_state(self, service):
        """Test soft deleting a board state."""
        state_id = BoardStateID(uuid4())
        existing_state = BoardState(
            id=state_id,
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            primary_value=100.0,
        )

        service.repository.get_by_id = AsyncMock(return_value=existing_state)
        service.repository.update = AsyncMock(return_value=existing_state)

        result = await service.soft_delete(state_id)

        assert result.is_deleted is True
        service.repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, service):
        """Test soft delete raises when state not found."""
        state_id = BoardStateID(uuid4())

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.soft_delete(state_id)
