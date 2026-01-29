"""Tests for ScoreEvent domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.scores.domain.score_event import ScoreEvent


class TestScoreEvent:
    """Test suite for ScoreEvent domain model."""

    def test_create_score_event_with_value_payload(self):
        """Test creating a score event with a value payload (for RUN boards)."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1000},
            is_test=False,
            timezone="America/New_York",
            country="US",
            city="New York",
            created_at=now,
        )

        assert event.id == event_id
        assert event.account_id == account_id
        assert event.game_id == game_id
        assert event.board_id == board_id
        assert event.identity_id == identity_id
        assert event.event_payload == {"value": 1000}
        assert event.is_test is False
        assert event.timezone == "America/New_York"
        assert event.country == "US"
        assert event.city == "New York"
        assert event.created_at == now

    def test_create_score_event_with_delta_payload(self):
        """Test creating a score event with a delta payload (for COUNTER boards)."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": 5},
            is_test=False,
            created_at=now,
        )

        assert event.event_payload == {"delta": 5}

    def test_create_score_event_with_test_flag(self):
        """Test creating a score event marked as test."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 500},
            is_test=True,
            created_at=now,
        )

        assert event.is_test is True

    def test_create_score_event_with_optional_geo_fields_none(self):
        """Test that score event can be created with optional geo fields as None."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            is_test=False,
            created_at=now,
        )

        assert event.timezone is None
        assert event.country is None
        assert event.city is None

    def test_account_id_required(self):
        """Test that account_id is required."""
        event_id = ScoreEventID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ScoreEvent(  # type: ignore[call-arg]
                id=event_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": 100},
                is_test=False,
                created_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_game_id_required(self):
        """Test that game_id is required."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ScoreEvent(  # type: ignore[call-arg]
                id=event_id,
                account_id=account_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": 100},
                is_test=False,
                created_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_board_id_required(self):
        """Test that board_id is required."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ScoreEvent(  # type: ignore[call-arg]
                id=event_id,
                account_id=account_id,
                game_id=game_id,
                identity_id=identity_id,
                event_payload={"value": 100},
                is_test=False,
                created_at=now,
            )

        assert "board_id" in str(exc_info.value)

    def test_identity_id_required(self):
        """Test that identity_id is required."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ScoreEvent(  # type: ignore[call-arg]
                id=event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                event_payload={"value": 100},
                is_test=False,
                created_at=now,
            )

        assert "identity_id" in str(exc_info.value)

    def test_event_payload_required(self):
        """Test that event_payload is required."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ScoreEvent(  # type: ignore[call-arg]
                id=event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                is_test=False,
                created_at=now,
            )

        assert "event_payload" in str(exc_info.value)

    def test_is_test_defaults_to_false(self):
        """Test that is_test defaults to False."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        assert event.is_test is False

    def test_score_event_has_no_updated_at(self):
        """Test that ScoreEvent does not have updated_at field (immutable entity)."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        # ScoreEvent should NOT have updated_at attribute
        assert not hasattr(event, "updated_at") or event.model_fields.get("updated_at") is None

    def test_score_event_has_no_deleted_at(self):
        """Test that ScoreEvent does not have deleted_at field (append-only)."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        # ScoreEvent should NOT have deleted_at attribute
        assert not hasattr(event, "deleted_at") or event.model_fields.get("deleted_at") is None

    def test_score_event_equality_based_on_id(self):
        """Test that score event equality is based on ID."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event1 = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            is_test=False,
            created_at=now,
        )

        event2 = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200},  # Different payload
            is_test=True,  # Different test flag
            created_at=now,
        )

        assert event1 == event2

    def test_score_event_inequality_different_ids(self):
        """Test that score events with different IDs are not equal."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event1 = ScoreEvent(
            id=ScoreEventID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        event2 = ScoreEvent(
            id=ScoreEventID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        assert event1 != event2

    def test_score_event_id_auto_generated(self):
        """Test that score event ID is auto-generated when not provided."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        assert event.id is not None
        assert isinstance(event.id, ScoreEventID)

    def test_score_event_created_at_auto_generated(self):
        """Test that created_at is auto-generated when not provided."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        event = ScoreEvent(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
        )

        assert event.created_at is not None
        # Should be set to current time (within 1 second tolerance)
        assert (datetime.now(UTC) - event.created_at).total_seconds() < 1

    def test_score_event_with_complex_payload(self):
        """Test creating a score event with a complex payload."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        complex_payload = {
            "value": 1000,
            "metadata": {
                "level": 5,
                "character": "warrior",
                "items": ["sword", "shield"],
            },
        }

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload=complex_payload,
            created_at=now,
        )

        assert event.event_payload == complex_payload

    def test_score_event_hashable(self):
        """Test that score events are hashable (can be used in sets/dicts)."""
        event_id = ScoreEventID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        event = ScoreEvent(
            id=event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            created_at=now,
        )

        # Should be able to add to set without error
        event_set = {event}  # type: ignore[var-annotated]
        assert len(event_set) == 1

        # Should be able to use as dict key
        event_dict = {event: "test"}  # type: ignore[dict-item]
        assert event_dict[event] == "test"
