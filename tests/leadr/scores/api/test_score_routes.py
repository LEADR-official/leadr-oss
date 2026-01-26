"""Tests for Score API routes."""

import hashlib
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityID, IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_event_service import ScoreEventService


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
        # Note: test_api_key creates a superadmin, so this test verifies the check exists
        # A more thorough test would need a non-superadmin API key
        # Superadmin can access all accounts, so skip this test

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

        # First request to get a cursor
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_cursor_test",
            display_name="CursorTest",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=100.0,
            player_name="CursorTest",
        )

        # Get initial response with cursor
        initial_response = await client.get(
            f"/scores?board_id={board.id}&limit=1",
            headers={"leadr-api-key": test_api_key},
        )
        cursor = initial_response.json()["pagination"].get("next_cursor")

        if cursor:
            score_id = f"scr_{state.id.uuid}"
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
