"""Tests for Board State API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardStateRoutes:
    """Test suite for Board State API routes."""

    async def test_list_board_states(self, client: AsyncClient, db_session, test_api_key):
        """Test listing board states via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-states",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_1",
            display_name="Player1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_2",
            display_name="Player2",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity1.id,
            primary_value=100.0,
            player_name="Player1",
        )
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity2.id,
            primary_value=200.0,
            player_name="Player2",
        )

        response = await client.get(
            f"/board-states?board_id={board.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2

    async def test_list_board_states_filter_by_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering board states by board_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-state-board",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_board_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        await state_service.create_board_state(
            board_id=board1.id,
            identity_id=identity.id,
            primary_value=100.0,
            player_name="TestPlayer",
        )
        await state_service.create_board_state(
            board_id=board2.id,
            identity_id=identity.id,
            primary_value=200.0,
            player_name="TestPlayer",
        )

        response = await client.get(
            f"/board-states?board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["board_id"] == str(board1.id)

    async def test_list_board_states_filter_by_identity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering board states by identity_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-state-identity",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_id_1",
            display_name="Player1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_id_2",
            display_name="Player2",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity1.id,
            primary_value=100.0,
            player_name="Player1",
        )
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity2.id,
            primary_value=200.0,
            player_name="Player2",
        )

        response = await client.get(
            f"/board-states?identity_id={identity1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["identity_id"] == str(identity1.id)

    async def test_get_board_state_by_id(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single board state by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-state-get",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_get_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="TestPlayer",
        )

        response = await client.get(
            f"/board-states/{state.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(state.id)
        assert data["primary_value"] == 500.0
        assert data["board_id"] == str(board.id)
        assert data["identity_id"] == str(identity.id)

    async def test_get_board_state_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent board state returns 404."""
        response = await client.get(
            "/board-states/bst_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_board_states_pagination(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test pagination of board states."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-state-pag",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        for i in range(15):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_state_pag_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )

        response = await client.get(
            f"/board-states?board_id={board.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

    async def test_list_board_states_combined_filters(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering board states by both board_id and identity_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-state-combined",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_state_combined_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="TestPlayer",
        )

        response = await client.get(
            f"/board-states?board_id={board.id}&identity_id={identity.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["board_id"] == str(board.id)
        assert data["data"][0]["identity_id"] == str(identity.id)
