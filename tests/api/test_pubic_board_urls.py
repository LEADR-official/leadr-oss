"""Integration tests for public board URL access patterns."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.services.api_key_service import APIKeyService
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.ids import AccountID
from leadr.games.domain.game import Game
from leadr.games.services.game_service import GameService


@pytest_asyncio.fixture
async def account_with_boards(db_session: AsyncSession):
    # Create account and API key
    account_repo = AccountRepository(db_session)
    account_id = AccountID()
    now = datetime.now(UTC)

    account = Account(
        id=account_id,
        name="Test Account",
        slug="test-account",
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await account_repo.create(account)

    # Create user for API key (superadmin to allow creating accounts)
    user_service = UserService(db_session)
    user = await user_service.create_user(
        account_id=account_id,
        email=f"test-{str(account_id)[:8]}@example.com",
        display_name="Test User",
        super_admin=True,
    )

    # Create API key
    api_key_service = APIKeyService(db_session)
    api_key, plain_key = await api_key_service.create_api_key(
        account_id=account_id,
        user_id=user.id,
        name="Test Key",
        expires_at=None,
    )

    # Create a game
    game_service = GameService(db_session)
    game = await game_service.create_game(
        account_id=account_id,
        name="Test Game",
        slug="test-game",
        steam_app_id=None,
        default_board_id=None,
        anti_cheat_enabled=False,
    )

    # Create two boards
    board_service = BoardService(db_session)
    board1 = await board_service.create_board(
        account_id=account_id,
        game_id=game.id,
        name="Weekly Challenge",
        icon="trophy",
        unit="points",
        is_active=True,
        sort_direction=SortDirection.DESCENDING,
        keep_strategy=KeepStrategy.BEST_ONLY,
        slug="weekly-challenge",
        short_code="WEEKLY",
        created_from_template_id=None,
        template_name=None,
        starts_at=None,
        ends_at=None,
        tags=None,
    )

    board2 = await board_service.create_board(
        account_id=account_id,
        game_id=game.id,
        name="Daily Sprint",
        icon="stopwatch",
        unit="seconds",
        is_active=True,
        sort_direction=SortDirection.ASCENDING,
        keep_strategy=KeepStrategy.BEST_ONLY,
        slug="daily-sprint",
        short_code="DAILY",
        created_from_template_id=None,
        template_name=None,
        starts_at=None,
        ends_at=None,
        tags=None,
    )

    boards = [board1, board2]

    return plain_key, account, game, boards


@pytest.mark.asyncio
class TestBoardURLs:
    """Integration tests for public board URL access patterns."""

    async def test_get_account_by_slug(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test GET /v1/accounts?slug={slug} for public account access."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/accounts",
            params={"slug": account.slug},
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify single item returned in paginated response
        assert data["pagination"]["count"] == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False

        # Verify account details
        assert len(data["data"]) == 1
        account_data = data["data"][0]
        assert account_data["slug"] == "test-account"
        assert account_data["name"] == "Test Account"
        assert account_data["id"] == str(account.id)

    async def test_get_game_by_slug(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test GET /v1/games?slug={slug} for public game access."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/games",
            params={"slug": game.slug, "account_id": str(account.id)},
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify single item returned in paginated response
        assert data["pagination"]["count"] == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False

        # Verify game details
        assert len(data["data"]) == 1
        game_data = data["data"][0]
        assert game_data["slug"] == "test-game"
        assert game_data["name"] == "Test Game"
        assert game_data["id"] == str(game.id)

    async def test_list_boards_by_game_slug(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test GET /v1/boards?game_slug={game_slug} for listing all boards in a game."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/boards",
            params={"game_slug": game.slug, "account_id": str(account.id)},
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify both boards returned
        assert len(data["data"]) == 2
        assert data["pagination"]["count"] == 2

        # Verify board slugs
        board_slugs = {board_data["slug"] for board_data in data["data"]}
        assert board_slugs == {"weekly-challenge", "daily-sprint"}

        # Verify all boards belong to the game
        for board_data in data["data"]:
            assert board_data["game_id"] == str(game.id)

    async def test_get_specific_board_by_game_and_slug(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test GET /v1/boards?game_slug={game_slug}&slug={slug} for specific board access."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/boards",
            params={
                "game_slug": game.slug,
                "slug": "weekly-challenge",
                "account_id": str(account.id),
            },
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify single board returned in paginated response
        assert data["pagination"]["count"] == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False

        # Verify board details
        assert len(data["data"]) == 1
        board_data = data["data"][0]
        assert board_data["slug"] == "weekly-challenge"
        assert board_data["name"] == "Weekly Challenge"
        assert board_data["game_id"] == str(game.id)
        assert board_data["short_code"] == "WEEKLY"

    async def test_board_slug_without_game_slug_fails(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test that board slug filter requires game_slug parameter."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/boards",
            params={"slug": "weekly-challenge", "account_id": str(account.id)},
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 400
        response_data = response.json()
        # Check for error message in either "detail" or "error" key
        error_msg = response_data.get("detail") or response_data.get("error", "")
        assert error_msg, f"No error message found in response: {response_data}"
        assert "game_slug parameter is required" in str(error_msg).lower()

    async def test_nonexistent_game_slug_returns_404(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test that nonexistent game slug returns 404."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/boards",
            params={"game_slug": "nonexistent-game", "account_id": str(account.id)},
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 404
        response_data = response.json()
        error_msg = str(response_data.get("detail", response_data.get("error", ""))).lower()
        assert "not found" in error_msg

    async def test_nonexistent_board_slug_returns_empty_list(
        self, client: AsyncClient, account_with_boards: tuple[str, Account, Game, list[Board]]
    ):
        """Test that nonexistent board slug returns empty list."""
        api_key, account, game, boards = account_with_boards

        response = await client.get(
            "/boards",
            params={
                "game_slug": game.slug,
                "slug": "nonexistent-board",
                "account_id": str(account.id),
            },
            headers={"leadr-api-key": api_key},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["data"] == []
