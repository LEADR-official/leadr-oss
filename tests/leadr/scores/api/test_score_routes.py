"""Tests for Score API routes."""

import hashlib
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.dependencies import get_user_service
from leadr.auth.domain.identity import IdentityID, IdentityKind
from leadr.auth.services.dependencies import get_api_key_service
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import FlagAction
from leadr.scores.services.score_event_service import ScoreEventService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreRoutesAdmin:
    """Test suite for Admin Score API routes."""

    async def test_get_score_by_id_board_state(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a BoardState score by ID returns rank."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-acc")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_player1",
            display_name="Player1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_player2",
            display_name="Player2",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        # Create board states directly
        state_service = BoardStateService(db_session)
        state1 = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity1.id,
            primary_value=500.0,
            player_name="Player1",
        )
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity2.id,
            primary_value=300.0,
            player_name="Player2",
        )

        # Get the score - use scr_ prefix
        score_id = f"scr_{state1.id.uuid}"
        response = await client.get(
            f"/scores/{score_id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == score_id
        assert data["rank"] == 1  # Highest score gets rank 1

    async def test_get_score_by_id_run_entry(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a RunEntry score by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-acc-run")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_runner",
            display_name="Runner",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,  # Lower is better
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 120.5},
        )

        # Create run entry
        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.create_run_entry(
            board_id=board.id,
            identity_id=identity.id,
            score_event_id=event.id,
            primary_value=120.5,
            player_name="Runner",
        )

        score_id = f"scr_{entry.id.uuid}"
        response = await client.get(
            f"/scores/{score_id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == score_id
        assert data["value"] == 120.5

    async def test_get_score_not_found(self, client: AsyncClient, test_api_key):
        """Test getting a non-existent score returns 404."""
        response = await client.get(
            "/scores/scr_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 404

    async def test_get_score_forbidden_different_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that accessing a score from another account is forbidden for non-superadmins."""
        # Create Account 1 (where the score will live)
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(name="Account 1", slug="acc1-forbidden")

        game_service = GameService(db_session)
        game1 = await game_service.create_game(account_id=account1.id, name="Game 1")

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board 1",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account1.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="acc1_player",
            display_name="Player1",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board1.id,
            identity_id=identity1.id,
            primary_value=500.0,
            player_name="Player1",
        )

        # Create Account 2 with a non-superadmin user
        account2 = await account_service.create_account(name="Account 2", slug="acc2-forbidden")

        user_service = await get_user_service(db_session)
        user2 = await user_service.create_user(
            account_id=account2.id,
            email="nonsuperadmin@example.com",
            display_name="Non-Admin",
            super_admin=False,  # NOT a superadmin
        )

        api_key_service = await get_api_key_service(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account2.id,
            user_id=user2.id,
            name="Non-Admin Key",
            expires_at=None,
        )

        # Try to access Account 1's score with Account 2's non-superadmin API key
        score_id = f"scr_{state.id.uuid}"
        response = await client.get(
            f"/scores/{score_id}",
            headers={"leadr-api-key": plain_key},
        )

        assert response.status_code == 403
        assert "access" in response.json()["error"].lower()

    async def test_list_scores_requires_board_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that list scores requires board_id."""
        response = await client.get(
            "/scores",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400
        assert "board_id is required" in response.json()["error"]

    async def test_list_scores_board_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test list scores with non-existent board."""
        response = await client.get(
            "/scores?board_id=brd_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 404

    async def test_list_scores_with_pagination(self, client: AsyncClient, db_session, test_api_key):
        """Test listing scores with pagination."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-pag")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create multiple identities and states
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        for i in range(15):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_player_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )

        # Request first page
        response = await client.get(
            f"/scores?board_id={board.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

    async def test_list_scores_around_score_id(self, client: AsyncClient, db_session, test_api_key):
        """Test listing scores centered around a specific score."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-around")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 10 scores with values 100-1000
        states = []
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_around_{i}",
                display_name=f"Player{i}",
            )
            state = await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )
            states.append(state)

        # Get around the middle score (500 points = rank 6 in desc order)
        target_state = states[4]  # 500 points
        score_id = f"scr_{target_state.id.uuid}"

        response = await client.get(
            f"/scores?board_id={board.id}&around_score_id={score_id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        # Should return scores around the target
        assert len(data["data"]) == 5

    async def test_list_scores_around_score_id_and_cursor_mutually_exclusive(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_id and cursor cannot be used together."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-mutual")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create multiple scores to ensure we get a cursor
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        states = []
        for i in range(5):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_cursor_mutual_{i}",
                display_name=f"CursorPlayer{i}",
            )
            state = await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"CursorPlayer{i}",
            )
            states.append(state)

        # Get initial response with limit=2 to get a cursor (5 items, limit 2 = has next)
        initial_response = await client.get(
            f"/scores?board_id={board.id}&limit=2&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )
        cursor = initial_response.json()["pagination"].get("next_cursor")
        assert cursor is not None, "Expected a cursor with 5 scores and limit=2"

        # Now try to use cursor AND around_score_id together - should fail
        score_id = f"scr_{states[2].id.uuid}"
        response = await client.get(
            f"/scores?board_id={board.id}&around_score_id={score_id}&cursor={cursor}",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400
        assert "cursor" in response.json()["error"].lower()

    async def test_list_scores_around_score_id_requires_board_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_id requires board_id."""
        response = await client.get(
            "/scores?around_score_id=scr_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400

    async def test_list_scores_around_score_value(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing scores around a hypothetical value."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-value")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create scores at 100, 200, 300, 400, 500
        for i in range(5):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_value_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )

        # Get around value 250 (between 200 and 300)
        response = await client.get(
            f"/scores?board_id={board.id}&around_score_value=250&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        # Should include a placeholder entry
        placeholders = [d for d in data["data"] if d.get("is_placeholder")]
        assert len(placeholders) == 1
        assert placeholders[0]["value"] == 250.0

    async def test_list_scores_around_score_value_requires_board_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_value requires board_id."""
        response = await client.get(
            "/scores?around_score_value=100",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400

    async def test_list_scores_around_score_value_and_cursor_mutually_exclusive(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_value and cursor cannot be used together."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-val-cur")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create multiple scores to ensure we get a cursor
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        for i in range(5):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_val_cursor_{i}",
                display_name=f"ValPlayer{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"ValPlayer{i}",
            )

        # Get initial response with limit=2 to get a cursor
        initial_response = await client.get(
            f"/scores?board_id={board.id}&limit=2&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )
        cursor = initial_response.json()["pagination"].get("next_cursor")
        assert cursor is not None, "Expected a cursor with 5 scores and limit=2"

        # Now try to use cursor AND around_score_value together - should fail
        response = await client.get(
            f"/scores?board_id={board.id}&around_score_value=150&cursor={cursor}",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400
        assert "cursor" in response.json()["error"].lower()

    async def test_list_scores_around_value_and_id_mutually_exclusive(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_id and around_score_value cannot be used together."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-both")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            f"/scores?board_id={board.id}&around_score_id=scr_00000000-0000-0000-0000-000000000000&around_score_value=100",
            headers={"leadr-api-key": test_api_key},
        )
        assert response.status_code == 400
        assert "around_score_id" in response.json()["error"].lower()

    async def test_list_scores_is_test_filter_true(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering scores by is_test=true."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-filter")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create test and prod scores
        for i, is_test in enumerate([True, False, True]):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_test_filter_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
                is_test=is_test,
            )

        response = await client.get(
            f"/scores?board_id={board.id}&is_test=true",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert all(d["is_test"] for d in data["data"])

    async def test_list_scores_is_test_filter_false(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering scores by is_test=false (default)."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-false")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create test and prod scores
        for i, is_test in enumerate([True, False, False]):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_prod_filter_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
                is_test=is_test,
            )

        # Default is_test=false
        response = await client.get(
            f"/scores?board_id={board.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert all(not d["is_test"] for d in data["data"])

    async def test_list_scores_is_test_filter_all(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing all scores regardless of is_test."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-all")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create test and prod scores
        for i, is_test in enumerate([True, False, True]):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_all_filter_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
                is_test=is_test,
            )

        response = await client.get(
            f"/scores?board_id={board.id}&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    async def test_list_scores_run_runs_board(self, client: AsyncClient, db_session, test_api_key):
        """Test listing scores from a RUN_RUNS board returns RunEntry data."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-runs")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_speedrunner",
            display_name="Speedrunner",
        )

        event_service = ScoreEventService(db_session)
        run_entry_service = RunEntryService(db_session)

        # Create multiple runs
        for i in range(5):
            event = await event_service.create_score_event(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                identity_id=identity.id,
                event_payload={"value": float(100 + i * 10)},
            )
            await run_entry_service.create_run_entry(
                board_id=board.id,
                identity_id=identity.id,
                score_event_id=event.id,
                primary_value=float(100 + i * 10),
                player_name="Speedrunner",
            )

        response = await client.get(
            f"/scores?board_id={board.id}&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5


@pytest.mark.asyncio
class TestScoreRoutesClient:
    """Test suite for Client Score API routes."""

    async def test_create_score_client(self, client: AsyncClient, db_session):
        """Test creating a score via client API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-client")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API (creates device and identity)
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        # Create score with nonce
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 1000.0,
                "player_name": "TestPlayer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["value"] == 1000.0
        assert data["player_name"] == "TestPlayer"

    async def test_create_score_board_not_found(self, client: AsyncClient, db_session):
        """Test creating a score with non-existent board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-404")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        response = await client.post(
            "/client/scores",
            json={
                "board_id": "brd_00000000-0000-0000-0000-000000000000",
                "value": 100.0,
                "player_name": "TestPlayer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )

        assert response.status_code == 404

    async def test_create_score_board_wrong_game(self, client: AsyncClient, db_session):
        """Test creating a score on a board from a different game."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-wrong")

        game_service = GameService(db_session)
        game1 = await game_service.create_game(account_id=account.id, name="Game 1")
        game2 = await game_service.create_game(account_id=account.id, name="Game 2")

        board_service = BoardService(db_session)
        # Board belongs to game2
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game2.id,
            name="Game 2 Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session for game1 via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game1.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        # Try to create score on board from game2
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 100.0,
                "player_name": "TestPlayer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )

        assert response.status_code == 400
        assert "does not belong" in response.json()["error"].lower()

    async def test_create_score_counter_board(self, client: AsyncClient, db_session):
        """Test creating a score on a COUNTER board uses delta."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-counter")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kill Counter",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce for first delta
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        # First delta
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 5.0,  # Used as delta for COUNTER
                "player_name": "Killer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["value"] == 5.0

        # Generate new nonce for second delta (nonces are single-use)
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        # Second delta - should accumulate
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 3.0,
                "player_name": "Killer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["value"] == 8.0  # 5 + 3

    async def test_get_score_client(self, client: AsyncClient, db_session):
        """Test getting a score via client API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-get-cl")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]

        # Create identity from session to use for board state
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(session_data["identity_id"]))
        assert identity is not None

        # Create board state directly
        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="TestPlayer",
        )

        # Get score
        score_id = f"scr_{state.id.uuid}"
        response = await client.get(
            f"/client/scores/{score_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 500.0

    async def test_get_score_client_wrong_game(self, client: AsyncClient, db_session):
        """Test getting a score from a different game returns 403."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-403")

        game_service = GameService(db_session)
        game1 = await game_service.create_game(account_id=account.id, name="Game 1")
        game2 = await game_service.create_game(account_id=account.id, name="Game 2")

        board_service = BoardService(db_session)
        # Board belongs to game2
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game2.id,
            name="Game 2 Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity for game2 and board state
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_game2_403",
            display_name="Game2Player",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity2.id,
            primary_value=500.0,
            player_name="Game2Player",
        )

        # Start session for game1 via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game1.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Try to get score from game2
        score_id = f"scr_{state.id.uuid}"
        response = await client.get(
            f"/client/scores/{score_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403

    async def test_list_scores_client(self, client: AsyncClient, db_session):
        """Test listing scores via client API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-list-cl")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]

        # Get the identity from the session to create board state
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(session_data["identity_id"]))
        assert identity is not None

        state_service = BoardStateService(db_session)
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="TestPlayer",
        )

        response = await client.get(
            f"/client/scores?board_id={board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    async def test_list_scores_client_with_identity_filter(self, client: AsyncClient, db_session):
        """Test listing client scores filtered by identity_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ident-f")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]

        # Get the identity from the session
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(session_data["identity_id"]))
        assert identity is not None

        # Create another identity with a different score
        other_identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="other_player",
            display_name="OtherPlayer",
        )

        state_service = BoardStateService(db_session)
        # Create score for our identity
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="TestPlayer",
        )
        # Create score for other identity
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=other_identity.id,
            primary_value=300.0,
            player_name="OtherPlayer",
        )

        # Filter by our identity_id - should only return our score
        response = await client.get(
            f"/client/scores?board_id={board.id}&identity_id={identity.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "TestPlayer"

    async def test_list_scores_client_run_runs_board(self, client: AsyncClient, db_session):
        """Test listing client scores from a RUN_RUNS board returns RunEntry data."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-runs-cl")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]

        # Get identity from session
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(session_data["identity_id"]))
        assert identity is not None

        # Create run entries
        event_service = ScoreEventService(db_session)
        run_entry_service = RunEntryService(db_session)

        for i in range(3):
            event = await event_service.create_score_event(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                identity_id=identity.id,
                event_payload={"value": float(100 + i * 10)},
            )
            await run_entry_service.create_run_entry(
                board_id=board.id,
                identity_id=identity.id,
                score_event_id=event.id,
                primary_value=float(100 + i * 10),
                player_name="Speedrunner",
            )

        response = await client.get(
            f"/client/scores?board_id={board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    async def test_get_score_client_run_entry(self, client: AsyncClient, db_session):
        """Test getting a RunEntry score via client API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-re-cl")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]

        # Get identity from session
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(session_data["identity_id"]))
        assert identity is not None

        # Create score event and run entry
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 120.5},
        )

        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.create_run_entry(
            board_id=board.id,
            identity_id=identity.id,
            score_event_id=event.id,
            primary_value=120.5,
            player_name="Speedrunner",
        )

        # Get the score
        score_id = f"scr_{entry.id.uuid}"
        response = await client.get(
            f"/client/scores/{score_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 120.5

    async def test_list_scores_client_with_pagination(self, client: AsyncClient, db_session):
        """Test that client list_scores returns proper pagination metadata."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-pag-cl")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 10 scores
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_pag_client_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )

        # Request first page with small limit - this exercises client pagination path
        response = await client.get(
            f"/client/scores?board_id={board.id}&limit=3",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["pagination"]["has_next"] is True
        # Client endpoint builds cursor with next_position which exercises cursor building code
        assert data["pagination"]["next_cursor"] is not None

    async def test_create_score_anti_cheat_reject(self, client: AsyncClient, db_session):
        """Test that anti-cheat REJECT returns 429."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-reject")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        nonce_value = nonce_response.json()["nonce_value"]

        # Mock the anti-cheat to return REJECT
        class MockAntiCheatResult:
            action = FlagAction.REJECT
            reason = "Rate limit exceeded"
            flags = []

        async def mock_submit_score(*args, **kwargs):
            # Return a tuple that matches (event, ranking_entry, anti_cheat_result)
            return (None, None, MockAntiCheatResult())

        with patch.object(
            db_session, "_score_service_submit_score", mock_submit_score, create=True
        ):
            # Actually patch the service method
            with patch.object(ScoreService, "submit_score", mock_submit_score):
                response = await client.post(
                    "/client/scores",
                    json={
                        "board_id": str(board.id),
                        "value": 1000.0,
                        "player_name": "TestPlayer",
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "leadr-client-nonce": nonce_value,
                    },
                )

        assert response.status_code == 429
        assert "Rate limit" in response.json()["error"]

    async def test_list_scores_admin_invalid_cursor(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test list scores with invalid cursor returns 400."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-bad-cur")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            f"/scores?board_id={board.id}&cursor=invalid_cursor_value",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400

    async def test_list_scores_admin_with_identity_filter(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing admin scores filtered by identity_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ident-a")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create two identities with scores
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="identity_a",
            display_name="PlayerA",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="identity_b",
            display_name="PlayerB",
        )

        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity1.id,
            primary_value=500.0,
            player_name="PlayerA",
        )
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity2.id,
            primary_value=300.0,
            player_name="PlayerB",
        )

        # Filter by identity1 - should only return their score
        response = await client.get(
            f"/scores?board_id={board.id}&identity_id={identity1.id}&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "PlayerA"

    async def test_list_scores_admin_with_pagination_cursors(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin list_scores returns proper pagination cursors."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-pag-adm")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 10 scores
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_pag_admin_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )

        # Request first page with small limit
        response = await client.get(
            f"/scores?board_id={board.id}&limit=3&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["next_cursor"] is not None

        # Use next_cursor to get next page
        next_cursor = data["pagination"]["next_cursor"]
        response2 = await client.get(
            f"/scores?board_id={board.id}&limit=3&cursor={next_cursor}&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]) == 3
        # Should have prev_cursor now
        assert data2["pagination"]["prev_cursor"] is not None

    async def test_list_scores_around_score_id_returns_absolute_ranks(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """GET /scores with around_score_id returns correct absolute ranks.

        When querying around a score at rank 6 with 10 scores total,
        the response should show ranks [4, 5, 6, 7, 8] not [1, 2, 3, 4, 5].
        """
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-abs-rank")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 10 scores with values 100-1000 (ranks 10 to 1 in DESC order)
        states = []
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_absrank_{i}",
                display_name=f"Player{i}",
            )
            state = await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )
            states.append(state)

        # Target: value 500 = rank 6 (in DESC order: 1000=1, 900=2, ... 500=6)
        target_state = states[4]  # 500 points
        score_id = f"scr_{target_state.id.uuid}"

        response = await client.get(
            f"/scores?board_id={board.id}&around_score_id={score_id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5

        # Check ranks are absolute (not relative)
        # Expected: ranks [4, 5, 6, 7, 8] for values [700, 600, 500, 400, 300]
        ranks = [score["rank"] for score in data["data"]]
        assert ranks == [4, 5, 6, 7, 8], f"Expected absolute ranks [4, 5, 6, 7, 8], got {ranks}"

        # Also verify values are correct (client response uses "value" not "primary_value")
        values = [score["value"] for score in data["data"]]
        assert values == [700.0, 600.0, 500.0, 400.0, 300.0]

    async def test_list_scores_around_score_value_returns_absolute_ranks(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """GET /scores with around_score_value returns correct absolute ranks.

        When querying around a hypothetical value with placeholder,
        all items should have correct absolute ranks.
        """
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-val-rank")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 7 scores with values 100-700 (ranks 7 to 1 in DESC order)
        for i in range(7):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_valrank_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )

        # Query around value 450 (between 400 and 500, hypothetical rank 4)
        response = await client.get(
            f"/scores?board_id={board.id}&around_score_value=450&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5

        # Expected: values [600, 500, 450 (placeholder), 400, 300]
        # Ranks should be [2, 3, 4, 5, 6] (absolute ranks)
        values = [score["value"] for score in data["data"]]
        assert values == [600.0, 500.0, 450.0, 400.0, 300.0]

        ranks = [score["rank"] for score in data["data"]]
        assert ranks == [2, 3, 4, 5, 6], f"Expected absolute ranks [2, 3, 4, 5, 6], got {ranks}"

        # Verify placeholder is marked
        assert data["data"][2]["is_placeholder"] is True

    async def test_list_scores_standard_pagination_returns_absolute_ranks(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Standard list_scores pagination returns correct absolute ranks.

        When querying page 2 (offset 5), ranks should be [6, 7, 8, ...] not [1, 2, 3, ...].
        """
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-std-rank")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Leaderboard",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        # Create 10 scores with values 100-1000
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_stdrank_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )

        # Get first page to obtain cursor
        response1 = await client.get(
            f"/scores?board_id={board.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # First page should have ranks [1, 2, 3, 4, 5]
        ranks1 = [score["rank"] for score in data1["data"]]
        assert ranks1 == [1, 2, 3, 4, 5], (
            f"First page: expected ranks [1, 2, 3, 4, 5], got {ranks1}"
        )

        # Get second page using cursor
        next_cursor = data1["pagination"]["next_cursor"]
        response2 = await client.get(
            f"/scores?board_id={board.id}&limit=5&cursor={next_cursor}",
            headers={"leadr-api-key": test_api_key},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Second page should have ranks [6, 7, 8, 9, 10]
        ranks2 = [score["rank"] for score in data2["data"]]
        assert ranks2 == [6, 7, 8, 9, 10], (
            f"Second page: expected ranks [6, 7, 8, 9, 10], got {ranks2}"
        )

    async def test_create_score_persists_display_name_to_identity(
        self, client: AsyncClient, db_session
    ):
        """Test that submitting a score with player_name persists it to identity.display_name."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-identity-dn")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Start session via API (creates device and identity)
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": fingerprint,
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        access_token = session_data["access_token"]
        identity_id = session_data["identity_id"]

        # Identity should have no display_name initially
        assert session_data["display_name"] is None

        # Generate nonce
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_value = nonce_response.json()["nonce_value"]

        # Submit score with player_name
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 1000.0,
                "player_name": "CoolPlayer",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce_value,
            },
        )
        assert response.status_code == 201
        assert response.json()["player_name"] == "CoolPlayer"

        # Verify identity.display_name was persisted in the database
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity = await identity_service.get_identity(IdentityID(identity_id))
        assert identity is not None
        assert identity.display_name == "CoolPlayer"
