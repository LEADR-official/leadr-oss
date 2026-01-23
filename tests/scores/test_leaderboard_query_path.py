"""Tests for leaderboard query path selection based on board type."""

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
class TestQueryPathSelection:
    """Tests for selecting query path based on board_type."""

    async def test_run_identity_board_queries_board_states(self):
        """RUN_IDENTITY boards should query board_states for leaderboard."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        # Create test identity
        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test123",
            display_name="TestPlayer",
        )

        # Create test score event
        score_event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1000.0},
            is_test=False,
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        # Create board state
        board_state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.0,
            aux={"selected_event_id": str(score_event_id.uuid), "event_count": 1},
        )

        # Transform to ScoreResponse
        response = ScoreResponse.from_board_state(
            state=board_state,
            identity=identity,
            score_event=score_event,
            rank=1,
        )

        # Verify response has correct data
        assert response.id.prefix == "scr"
        assert response.value == 1000.0
        assert response.player_name == "TestPlayer"
        assert response.rank == 1
        assert response.timezone == "America/New_York"
        assert response.country == "US"
        assert response.city == "New York"

    async def test_run_runs_board_queries_run_entries(self):
        """RUN_RUNS boards should query run_entries for leaderboard."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()

        # Create test identity
        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_runner",
            display_name="SpeedRunner",
        )

        # Create test score event
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

        # Create run entry
        run_entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=123.45,
        )

        # Transform to ScoreResponse
        response = ScoreResponse.from_run_entry(
            entry=run_entry,
            identity=identity,
            score_event=score_event,
            rank=3,
        )

        # Verify response has correct data
        assert response.id.prefix == "scr"
        assert response.value == 123.45
        assert response.player_name == "SpeedRunner"
        assert response.rank == 3
        assert response.is_test is True
        assert response.timezone == "Europe/London"


@pytest.mark.asyncio
class TestLeaderboardRanking:
    """Tests for leaderboard ranking from board_states and run_entries."""

    async def test_board_state_responses_maintain_rank_order(self):
        """Multiple board states should maintain correct rank order in responses."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()

        # Create 3 identities with different scores
        identities_data = [
            ("Player1", 3000.0, 1),
            ("Player2", 2000.0, 2),
            ("Player3", 1000.0, 3),
        ]

        responses = []
        for display_name, value, rank in identities_data:
            identity_id = IdentityID()
            score_event_id = ScoreEventID()

            identity = Identity(
                id=identity_id,
                account_id=account_id,
                game_id=game_id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_{display_name.lower()}",
                display_name=display_name,
            )

            score_event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": value},
            )

            board_state = BoardState(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=value,
            )

            response = ScoreResponse.from_board_state(
                state=board_state,
                identity=identity,
                score_event=score_event,
                rank=rank,
            )
            responses.append(response)

        # Verify ranking
        assert responses[0].rank == 1
        assert responses[0].value == 3000.0
        assert responses[1].rank == 2
        assert responses[1].value == 2000.0
        assert responses[2].rank == 3
        assert responses[2].value == 1000.0

    async def test_run_entry_responses_maintain_rank_order(self):
        """Multiple run entries should maintain correct rank order in responses."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_runner",
            display_name="SpeedRunner",
        )

        # Create 3 run entries for same player with different times (ascending = lower is better)
        runs_data = [
            (45.2, 1),  # Best time
            (47.8, 2),
            (52.1, 3),  # Worst time
        ]

        responses = []
        for value, rank in runs_data:
            score_event_id = ScoreEventID()

            score_event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": value},
            )

            run_entry = RunEntry(
                board_id=board_id,
                identity_id=identity_id,
                score_event_id=score_event_id,
                primary_value=value,
            )

            response = ScoreResponse.from_run_entry(
                entry=run_entry,
                identity=identity,
                score_event=score_event,
                rank=rank,
            )
            responses.append(response)

        # Verify ranking (all same player, different runs)
        assert all(r.player_name == "SpeedRunner" for r in responses)
        assert responses[0].rank == 1
        assert responses[0].value == 45.2
        assert responses[1].rank == 2
        assert responses[1].value == 47.8
        assert responses[2].rank == 3
        assert responses[2].value == 52.1
