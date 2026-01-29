"""Tests for ScoreResponse transformation methods from BoardState and RunEntry."""

import pytest

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

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1500.0,
            aux={"event_count": 3},
            player_name="Test Player",
            is_test=False,
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        # Transform
        response = ScoreResponse.from_board_state(
            state=board_state,
            account_id=account_id,
            game_id=game_id,
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

    async def test_uses_denormalized_player_name(self):
        """Player name should come from denormalized field on board state."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="SteamPlayer42",
            is_test=False,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            account_id=account_id,
            game_id=game_id,
            rank=5,
        )

        assert response.player_name == "SteamPlayer42"

    async def test_handles_empty_player_name(self):
        """Should handle board state with empty player_name."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=50.0,
            player_name="",
            is_test=False,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            account_id=account_id,
            game_id=game_id,
            rank=10,
        )

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

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=123.45,
            player_name="SpeedRunner",
            is_test=True,
            timezone="Europe/London",
            country="GB",
            city="London",
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            account_id=account_id,
            game_id=game_id,
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

    async def test_run_entry_uses_own_timestamps(self):
        """Run entry response should use run_entry's timestamps."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=200.0,
            player_name="TestPlayer",
            is_test=False,
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            account_id=account_id,
            game_id=game_id,
            rank=1,
        )

        # created_at should come from run_entry
        assert response.created_at == run_entry.created_at


@pytest.mark.asyncio
class TestScoreIDMasking:
    """Tests for score ID masking in transformations."""

    async def test_board_state_id_masked_to_score_id(self):
        """BoardState ID should be masked to look like ScoreID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Test",
            is_test=False,
        )

        response = ScoreResponse.from_board_state(
            state=board_state,
            account_id=account_id,
            game_id=game_id,
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

        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=100.0,
            player_name="Test",
            is_test=False,
        )

        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            account_id=account_id,
            game_id=game_id,
            rank=1,
        )

        # ID should have scr_ prefix but same UUID
        assert str(response.id).startswith("scr_")
        assert response.id.uuid == run_entry.id.uuid
