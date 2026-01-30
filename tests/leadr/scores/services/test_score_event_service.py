"""Tests for ScoreEventService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.score_event_service import ScoreEventService


@pytest.fixture
def mock_session():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def service(mock_session):
    """Create service with mocked repository."""
    svc = ScoreEventService(mock_session)
    svc.repository = MagicMock()
    return svc


@pytest.mark.asyncio
class TestScoreEventService:
    """Tests for ScoreEventService."""

    async def test_create_score_event(self, service):
        """Test creating a score event."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        event = await service.create_score_event(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1000},
        )

        assert event.id is not None
        assert isinstance(event.id, ScoreEventID)
        assert event.account_id == account_id
        assert event.game_id == game_id
        assert event.board_id == board_id
        assert event.identity_id == identity_id
        assert event.event_payload == {"value": 1000}
        assert event.is_test is False
        assert event.timezone is None
        assert event.country is None
        assert event.city is None

        service.repository.create.assert_called_once()
        created_event = service.repository.create.call_args[0][0]
        assert created_event.account_id == account_id
        assert created_event.event_payload == {"value": 1000}

    async def test_create_score_event_with_geo_data(self, service):
        """Test creating a score event with geo data."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        event = await service.create_score_event(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": 50},
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        assert event.timezone == "America/New_York"
        assert event.country == "US"
        assert event.city == "New York"

        service.repository.create.assert_called_once()
        created_event = service.repository.create.call_args[0][0]
        assert created_event.timezone == "America/New_York"
        assert created_event.country == "US"
        assert created_event.city == "New York"

    async def test_create_score_event_test_mode(self, service):
        """Test creating a test score event."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        event = await service.create_score_event(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 500},
            is_test=True,
        )

        assert event.is_test is True

        service.repository.create.assert_called_once()
        created_event = service.repository.create.call_args[0][0]
        assert created_event.is_test is True

    async def test_get_score_event(self, service):
        """Test retrieving a score event by ID."""
        event_id = ScoreEventID()
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        expected_event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_event)

        retrieved = await service.get_score_event(event_id)

        assert retrieved is not None
        assert retrieved.id == event_id
        assert retrieved.event_payload == {"value": 100}

        service.repository.get_by_id.assert_called_once_with(event_id)

    async def test_get_score_event_not_found(self, service):
        """Test getting a non-existent score event returns None."""
        event_id = ScoreEventID()

        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_score_event(event_id)

        assert result is None
        service.repository.get_by_id.assert_called_once_with(event_id)

    async def test_get_score_event_or_raise(self, service):
        """Test get_by_id_or_raise returns event when found."""
        event_id = ScoreEventID()
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        expected_event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_event)

        retrieved = await service.get_by_id_or_raise(event_id)

        assert retrieved.id == event_id
        service.repository.get_by_id.assert_called_once_with(event_id)

    async def test_get_score_event_or_raise_not_found(self, service):
        """Test get_by_id_or_raise raises when not found."""
        event_id = ScoreEventID()

        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.get_by_id_or_raise(event_id)

        assert "ScoreEvent" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(event_id)

    async def test_list_score_events_by_board(self, service):
        """Test listing score events filtered by board."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        events = [
            ScoreEvent(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": i * 100},
            )
            for i in range(3)
        ]

        paginated_result = PaginatedResult(
            items=events,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        service.repository.filter = AsyncMock(return_value=paginated_result)

        result = await service.list_score_events(board_id=board_id)

        assert len(result.items) == 3
        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args[1]
        assert call_kwargs["board_id"] == board_id

    async def test_list_score_events_by_identity(self, service):
        """Test listing score events filtered by identity."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        events = [
            ScoreEvent(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": i * 100},
            )
            for i in range(2)
        ]

        paginated_result = PaginatedResult(
            items=events,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        service.repository.filter = AsyncMock(return_value=paginated_result)

        result = await service.list_score_events(identity_id=identity_id)

        assert len(result.items) == 2
        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args[1]
        assert call_kwargs["identity_id"] == identity_id

    async def test_list_score_events_filter_is_test(self, service):
        """Test listing score events filtered by is_test flag."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        test_event = ScoreEvent(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200},
            is_test=True,
        )

        paginated_result = PaginatedResult(
            items=[test_event],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        service.repository.filter = AsyncMock(return_value=paginated_result)

        result = await service.list_score_events(board_id=board_id, is_test=True)

        assert len(result.items) == 1
        assert result.items[0].is_test is True
        assert result.items[0].event_payload == {"value": 200}

        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args[1]
        assert call_kwargs["is_test"] is True

    async def test_list_score_events_by_account(self, service):
        """Test listing score events filtered by account."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        event = ScoreEvent(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
        )

        paginated_result = PaginatedResult(
            items=[event],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        service.repository.filter = AsyncMock(return_value=paginated_result)

        result = await service.list_score_events(account_id=account_id)

        assert len(result.items) == 1
        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args[1]
        assert call_kwargs["account_id"] == account_id

    async def test_list_score_events_empty(self, service):
        """Test listing score events returns empty when none exist."""
        board_id = BoardID(uuid4())

        paginated_result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        service.repository.filter = AsyncMock(return_value=paginated_result)

        result = await service.list_score_events(board_id=board_id)

        assert len(result.items) == 0
        assert result.has_next is False
        assert result.has_prev is False

    async def test_score_events_are_immutable(self, service):
        """Test that score events cannot be updated (no update method)."""
        # ScoreEventService should NOT have update methods
        assert not hasattr(service, "update")
        assert not hasattr(service, "update_score_event")

    async def test_score_events_cannot_be_deleted(self, service):
        """Test that score events cannot be deleted (no delete method)."""
        # ScoreEventService should NOT have delete methods
        assert not hasattr(service, "delete")
        assert not hasattr(service, "delete_score_event")
        assert not hasattr(service, "soft_delete")
