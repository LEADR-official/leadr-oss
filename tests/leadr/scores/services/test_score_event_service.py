"""Tests for ScoreEventService."""

import pytest

from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.scores.services.score_event_service import ScoreEventService


@pytest.mark.asyncio
class TestScoreEventService:
    """Tests for ScoreEventService."""

    async def test_create_score_event(self, db_session, board_orm, identity_orm):
        """Test creating a score event."""
        service = ScoreEventService(db_session)

        event = await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 1000},
        )

        assert event.id is not None
        assert isinstance(event.id, ScoreEventID)
        assert event.account_id == AccountID(board_orm.account_id)
        assert event.game_id == GameID(board_orm.game_id)
        assert event.board_id == BoardID(board_orm.id)
        assert event.identity_id == IdentityID(identity_orm.id)
        assert event.event_payload == {"value": 1000}
        assert event.is_test is False
        assert event.timezone is None
        assert event.country is None
        assert event.city is None

    async def test_create_score_event_with_geo_data(self, db_session, board_orm, identity_orm):
        """Test creating a score event with geo data."""
        service = ScoreEventService(db_session)

        event = await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"delta": 50},
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        assert event.timezone == "America/New_York"
        assert event.country == "US"
        assert event.city == "New York"

    async def test_create_score_event_test_mode(self, db_session, board_orm, identity_orm):
        """Test creating a test score event."""
        service = ScoreEventService(db_session)

        event = await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 500},
            is_test=True,
        )

        assert event.is_test is True

    async def test_get_score_event(self, db_session, board_orm, identity_orm):
        """Test retrieving a score event by ID."""
        service = ScoreEventService(db_session)

        created = await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 100},
        )

        retrieved = await service.get_score_event(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.event_payload == {"value": 100}

    async def test_get_score_event_not_found(self, db_session):
        """Test getting a non-existent score event returns None."""
        service = ScoreEventService(db_session)

        result = await service.get_score_event(ScoreEventID())

        assert result is None

    async def test_get_score_event_or_raise(self, db_session, board_orm, identity_orm):
        """Test get_by_id_or_raise returns event when found."""
        service = ScoreEventService(db_session)

        created = await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 100},
        )

        retrieved = await service.get_by_id_or_raise(created.id)

        assert retrieved.id == created.id

    async def test_get_score_event_or_raise_not_found(self, db_session):
        """Test get_by_id_or_raise raises when not found."""
        from leadr.common.domain.exceptions import EntityNotFoundError

        service = ScoreEventService(db_session)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.get_by_id_or_raise(ScoreEventID())

        assert "ScoreEvent" in str(exc_info.value)

    async def test_list_score_events_by_board(self, db_session, board_orm, identity_orm):
        """Test listing score events filtered by board."""
        service = ScoreEventService(db_session)

        # Create multiple events
        for i in range(3):
            await service.create_score_event(
                account_id=AccountID(board_orm.account_id),
                game_id=GameID(board_orm.game_id),
                board_id=BoardID(board_orm.id),
                identity_id=IdentityID(identity_orm.id),
                event_payload={"value": i * 100},
            )

        result = await service.list_score_events(board_id=BoardID(board_orm.id))

        assert len(result.items) == 3

    async def test_list_score_events_by_identity(self, db_session, board_orm, identity_orm):
        """Test listing score events filtered by identity."""
        service = ScoreEventService(db_session)

        # Create events
        for i in range(2):
            await service.create_score_event(
                account_id=AccountID(board_orm.account_id),
                game_id=GameID(board_orm.game_id),
                board_id=BoardID(board_orm.id),
                identity_id=IdentityID(identity_orm.id),
                event_payload={"value": i * 100},
            )

        result = await service.list_score_events(identity_id=IdentityID(identity_orm.id))

        assert len(result.items) == 2

    async def test_list_score_events_filter_is_test(self, db_session, board_orm, identity_orm):
        """Test listing score events filtered by is_test flag."""
        service = ScoreEventService(db_session)

        # Create a production event
        await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 100},
            is_test=False,
        )

        # Create a test event
        await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 200},
            is_test=True,
        )

        # Filter for test events only
        result = await service.list_score_events(
            board_id=BoardID(board_orm.id),
            is_test=True,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is True
        assert result.items[0].event_payload == {"value": 200}

    async def test_list_score_events_by_account(self, db_session, board_orm, identity_orm):
        """Test listing score events filtered by account."""
        service = ScoreEventService(db_session)

        await service.create_score_event(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 100},
        )

        result = await service.list_score_events(account_id=AccountID(board_orm.account_id))

        assert len(result.items) == 1

    async def test_list_score_events_empty(self, db_session, board_orm):
        """Test listing score events returns empty when none exist."""
        service = ScoreEventService(db_session)

        result = await service.list_score_events(board_id=BoardID(board_orm.id))

        assert len(result.items) == 0
        assert result.has_next is False
        assert result.has_prev is False

    async def test_score_events_are_immutable(self, db_session, board_orm, identity_orm):
        """Test that score events cannot be updated (no update method)."""
        service = ScoreEventService(db_session)

        # ScoreEventService should NOT have update methods
        assert not hasattr(service, "update")
        assert not hasattr(service, "update_score_event")

    async def test_score_events_cannot_be_deleted(self, db_session, board_orm, identity_orm):
        """Test that score events cannot be deleted (no delete method)."""
        service = ScoreEventService(db_session)

        # ScoreEventService should NOT have delete methods
        assert not hasattr(service, "delete")
        assert not hasattr(service, "delete_score_event")
        assert not hasattr(service, "soft_delete")
