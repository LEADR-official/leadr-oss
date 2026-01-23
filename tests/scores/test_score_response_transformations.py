"""Tests for ScoreResponse transformation methods from BoardState and RunEntry."""

import pytest

from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.scores.api.score_schemas import ScoreResponse
from leadr.scores.domain.score_event import ScoreEvent


@pytest.mark.asyncio
class TestScoreResponseFromBoardState:
    """Tests for ScoreResponse.from_board_state transformation."""

    async def test_transforms_board_state_to_score_response(self):
        """Board state should transform to score response with masked ID."""
        # Create test data
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test123",
            display_name="Test Player",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1500.0},
            is_test=False,
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1500.0,
            aux={"selected_event_id": str(score_event_id.uuid), "event_count": 3},
        )

        # Transform
        response = ScoreResponse.from_board_state(
            state=board_state,
            identity=identity,
            score_event=score_event,
            rank=1,
        )

        # Verify ID is masked (bst_ -> scr_)
        assert response.id.prefix == "scr"
        assert response.id.uuid == board_state.id.uuid

        # Verify other fields
        assert response.account_id == account_id
        assert response.game_id == game_id
        assert response.board_id == board_id
        assert response.identity_id == identity_id
        assert response.player_name == "Test Player"
        assert response.value == 1500.0
        assert response.rank == 1
        assert response.is_test is False
        assert response.timezone == "America/New_York"
        assert response.country == "US"
        assert response.city == "New York"

    async def test_uses_identity_display_name(self):
        """Player name should come from identity display_name."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.STEAM,
            external_key="steam_12345",
            display_name="SteamPlayer42",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            identity=identity,
            score_event=score_event,
            rank=5,
        )

        assert response.player_name == "SteamPlayer42"

    async def test_handles_none_display_name(self):
        """Should handle identity with None display_name."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_anonymous",
            display_name=None,
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 50.0},
        )

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=50.0,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            identity=identity,
            score_event=score_event,
            rank=10,
        )

        # Should use empty string or a default when display_name is None
        assert response.player_name == ""


@pytest.mark.asyncio
class TestScoreResponseFromRunEntry:
    """Tests for ScoreResponse.from_run_entry transformation."""

    async def test_transforms_run_entry_to_score_response(self):
        """Run entry should transform to score response with masked ID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_runner",
            display_name="SpeedRunner",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 123.45},
            is_test=True,
            timezone="Europe/London",
            country="GB",
            city="London",
        )

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=123.45,
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            identity=identity,
            score_event=score_event,
            rank=3,
        )

        # Verify ID is masked (run_ -> scr_)
        assert response.id.prefix == "scr"
        assert response.id.uuid == run_entry.id.uuid

        # Verify other fields
        assert response.account_id == account_id
        assert response.game_id == game_id
        assert response.board_id == board_id
        assert response.identity_id == identity_id
        assert response.player_name == "SpeedRunner"
        assert response.value == 123.45
        assert response.rank == 3
        assert response.is_test is True
        assert response.timezone == "Europe/London"
        assert response.country == "GB"
        assert response.city == "London"

    async def test_run_entry_uses_score_event_created_at(self):
        """Run entry response should use score_event.created_at for timestamps."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test",
            display_name="TestPlayer",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200.0},
        )

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=200.0,
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            identity=identity,
            score_event=score_event,
            rank=1,
        )

        # created_at should come from score_event
        assert response.created_at == score_event.created_at


@pytest.mark.asyncio
class TestScoreIDMasking:
    """Tests for score ID masking in transformations."""

    async def test_board_state_id_masked_to_score_id(self):
        """BoardState ID should be masked to look like ScoreID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test",
            display_name="Test",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            identity=identity,
            score_event=score_event,
            rank=1,
        )

        # ID should have scr_ prefix but same UUID
        assert str(response.id).startswith("scr_")
        assert response.id.uuid == board_state.id.uuid

    async def test_run_entry_id_masked_to_score_id(self):
        """RunEntry ID should be masked to look like ScoreID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test",
            display_name="Test",
        )

        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=100.0,
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            identity=identity,
            score_event=score_event,
            rank=1,
        )

        # ID should have scr_ prefix but same UUID
        assert str(response.id).startswith("scr_")
        assert response.id.uuid == run_entry.id.uuid
