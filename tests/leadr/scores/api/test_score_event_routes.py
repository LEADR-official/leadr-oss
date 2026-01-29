"""Tests for Score Event API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.domain.ids import BoardID, IdentityID
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_event_service import ScoreEventService


@pytest.mark.asyncio
class TestScoreEventRoutes:
    """Test suite for Score Event API routes."""

    async def test_list_score_events(self, client: AsyncClient, db_session, test_api_key):
        """Test listing score events via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-events",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_event_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="EVT01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events
        event_service = ScoreEventService(db_session)
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # List events
        response = await client.get(
            f"/score-events?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2

    async def test_list_score_events_filter_by_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering score events by board_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-board",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_board_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # Filter by board1
        response = await client.get(
            f"/score-events?board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["board_id"] == str(board1.id)

    async def test_list_score_events_filter_by_identity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering score events by identity_id."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-identity",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_id_1",
            display_name="Player1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_id_2",
            display_name="Player2",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity1.id,
            event_payload={"value": 100.0},
        )
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity2.id,
            event_payload={"value": 200.0},
        )

        # Filter by identity1
        response = await client.get(
            f"/score-events?identity_id={identity1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["identity_id"] == str(identity1.id)

    async def test_list_score_events_filter_by_is_test(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering score events by is_test."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-test",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_test_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
            is_test=True,
        )
        await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
            is_test=False,
        )

        # Filter by is_test=true
        response = await client.get(
            f"/score-events?account_id={account.id}&is_test=true",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["is_test"] is True

    async def test_get_score_event_by_id(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single score event by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-get",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_get_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        response = await client.get(
            f"/score-events/{event.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(event.id)
        assert data["event_payload"]["value"] == 100.0

    async def test_get_score_event_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent score event returns 404."""
        response = await client.get(
            "/score-events/sev_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_get_score_event_wrong_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that non-superadmin cannot access events from another account.

        Note: The test_api_key fixture creates a superadmin, so this test
        documents the expected behavior but the superadmin can access all.
        """
        # This test would need a non-superadmin API key to properly test
        # the 403 behavior. For now, we just verify the endpoint works.
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-wrong",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_wrong_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Superadmin can access all accounts, so this returns 200
        response = await client.get(
            f"/score-events/{event.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

    async def test_list_score_events_pagination(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test pagination of score events."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-evt-pag",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_evt_pag_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        for i in range(15):
            await event_service.create_score_event(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                identity_id=identity.id,
                event_payload={"value": float(i * 100)},
            )

        # First page
        response = await client.get(
            f"/score-events?account_id={account.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True


@pytest.mark.asyncio
class TestCreateScoreEvent:
    """Test suite for POST /score-events endpoint."""

    async def test_create_score_event_creates_event_and_ranking(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event via POST /score-events."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-create-event",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_create_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event via API
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(board.id),
                "identity_id": str(identity.id),
                "value": 1000.0,
                "player_name": "TestPlayer",
                "is_test": False,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["board_id"] == str(board.id)
        assert data["identity_id"] == str(identity.id)
        assert data["event_payload"]["value"] == 1000.0
        assert data["is_test"] is False

        # Verify board state was created
        board_state_service = BoardStateService(db_session)
        state = await board_state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

    async def test_create_score_event_run_runs_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event on a RUN_RUNS board."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-create-runs",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_runs_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        # Create score event via API
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(board.id),
                "identity_id": str(identity.id),
                "value": 1500.0,
                "player_name": "TestPlayer",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_payload"]["value"] == 1500.0

        # Verify run entry was created
        run_entry_service = RunEntryService(db_session)
        result = await run_entry_service.list_run_entries(board_id=board.id)
        assert len(result.items) == 1
        assert result.items[0].primary_value == 1500.0

    async def test_create_score_event_counter_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event on a COUNTER board (value treated as delta)."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-create-counter",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_counter_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Counter Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.COUNTER,
        )

        # Create first score event (delta of 50)
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(board.id),
                "identity_id": str(identity.id),
                "value": 50.0,
                "player_name": "TestPlayer",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_payload"]["delta"] == 50.0

        # Verify board state has accumulated value
        board_state_service = BoardStateService(db_session)
        state = await board_state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 50.0

        # Create second score event (delta of 30)
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(board.id),
                "identity_id": str(identity.id),
                "value": 30.0,
                "player_name": "TestPlayer",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201

        # Verify board state accumulated (50 + 30 = 80)
        state = await board_state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 80.0

    async def test_create_score_event_board_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event with non-existent board returns 404."""

        # Use valid prefixed IDs
        fake_board_id = BoardID()
        fake_identity_id = IdentityID()

        response = await client.post(
            "/score-events",
            json={
                "board_id": str(fake_board_id),
                "identity_id": str(fake_identity_id),
                "value": 1000.0,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "Board not found" in response.json()["error"]

    async def test_create_score_event_ratio_board_rejected(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event on a RATIO board returns 400."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-ratio-reject",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_ratio_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        ratio_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Ratio Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RATIO,
        )

        # Try to create score event on ratio board
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(ratio_board.id),
                "identity_id": str(identity.id),
                "value": 1000.0,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "RATIO boards do not accept direct submissions" in response.json()["error"]

    async def test_create_score_event_with_geo_data(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score event with geographic data."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-geo-data",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_geo_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event with geo data
        response = await client.post(
            "/score-events",
            json={
                "board_id": str(board.id),
                "identity_id": str(identity.id),
                "value": 1000.0,
                "player_name": "TestPlayer",
                "timezone": "America/New_York",
                "country": "US",
                "city": "New York",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["timezone"] == "America/New_York"
        assert data["country"] == "US"
        assert data["city"] == "New York"
