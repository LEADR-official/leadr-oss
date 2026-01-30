"""Tests for Board API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestBoardRoutes:
    """Test suite for Board API routes."""

    async def test_create_board(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board via API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        # Mock service response
        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.create_board.return_value = created_board
        mock_board_ratio_config_service.create_ratio_config.return_value = None

        # Create board
        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Speed Run Board"
        assert data["short_code"] == "SR2025"
        assert data["account_id"] == str(account_id)
        assert data["game_id"] == str(game_id)
        assert "id" in data
        assert "created_at" in data

        # Verify service was called correctly
        mock_board_service.create_board.assert_called_once()
        call_kwargs = mock_board_service.create_board.call_args.kwargs
        assert call_kwargs["account_id"] == account_id
        assert call_kwargs["game_id"] == game_id
        assert call_kwargs["name"] == "Speed Run Board"

    async def test_create_board_with_optional_fields(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with optional fields via API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            tags=["speedrun", "no-damage"],
            template_name="Speed Run Template",
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST",
                "tags": ["speedrun", "no-damage"],
                "template_name": "Speed Run Template",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == ["speedrun", "no-damage"]
        assert data["template_name"] == "Speed Run Template"

    async def test_create_board_with_minimal_fields(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with minimal required fields using defaults."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Minimal Board",
            slug="minimal-board",
            short_code="ABCDE",
            icon="fa-crown",
            unit=None,
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Minimal Board",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Board"
        assert data["short_code"] is not None
        assert len(data["short_code"]) == 5
        assert data["icon"] == "fa-crown"
        assert data["unit"] is None
        assert data["is_active"] is True
        assert data["sort_direction"] == "DESCENDING"
        assert data["keep_strategy"] == "BEST"

    async def test_create_board_with_game_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with non-existent game returns 404."""
        account_id = admin_auth.account_id

        # Mock IntegrityError (foreign key violation)
        mock_board_service.create_board.side_effect = IntegrityError(
            "statement", "params", Exception("orig")
        )

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": "gam_00000000-0000-0000-0000-000000000000",
                "name": "Invalid Board",
                "icon": "star",
                "short_code": "INVALID",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_create_board_with_game_from_different_account(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with game from different account returns 400."""
        account_id = admin_auth.account_id
        game_id = GameID()

        # Mock ValueError for account mismatch
        mock_board_service.create_board.side_effect = ValueError("Game does not belong to account")

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Invalid Board",
                "icon": "star",
                "short_code": "INVALID",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response.status_code == 400
        assert "does not belong to account" in response.json()["error"].lower()

    async def test_get_board(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test retrieving a board by ID via API."""
        account_id = admin_auth.account_id
        board_id = BoardID()
        game_id = GameID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.get_by_id_or_raise.return_value = board
        mock_board_ratio_config_service.get_by_board_id.return_value = None

        response = await mock_client_no_db.get(f"/boards/{board_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(board_id)
        assert data["name"] == "Speed Run Board"

    async def test_get_board_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test retrieving a non-existent board returns 404."""
        board_id = BoardID()
        mock_board_service.get_by_id_or_raise.side_effect = EntityNotFoundError(
            "Board", str(board_id)
        )

        response = await mock_client_no_db.get(f"/boards/{board_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_boards_by_code(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test listing boards filtered by short code via API."""
        account_id = admin_auth.account_id
        board_id = BoardID()
        game_id = GameID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(f"/boards?code=SR2025&account_id={account_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == str(board_id)
        assert data["data"][0]["short_code"] == "SR2025"

    async def test_list_boards_by_code_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test listing boards by non-existent short code returns empty list."""
        result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get("/boards?code=NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 0

    async def test_list_boards_by_account_and_code(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test listing boards filtered by both account_id and code."""
        account_id = AccountID()
        board_id = BoardID()
        game_id = GameID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Account 2 Board",
            slug="account-2-board",
            icon="trophy",
            short_code="CODE2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(f"/boards?account_id={account_id}&code=CODE2")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == str(board_id)
        assert data["data"][0]["name"] == "Account 2 Board"

    async def test_list_boards(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test listing boards for an account via API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        board1 = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            slug="board-one",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            slug="board-two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board1, board2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(f"/boards?account_id={account_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        names = {b["name"] for b in data["data"]}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_list_boards_requires_account_id_or_code(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that listing boards defaults to authenticated user's account."""
        result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get("/boards")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    async def test_list_boards_filters_by_account(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that listing boards filters by account."""
        account1_id = AccountID()
        game_id = GameID()

        board = Board(
            id=BoardID(),
            account_id=account1_id,
            game_id=game_id,
            name="Account 1 Board",
            slug="account-1-board",
            icon="star",
            short_code="A1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(f"/boards?account_id={account1_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Account 1 Board"

    async def test_update_board(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test updating a board via API."""
        account_id = admin_auth.account_id
        board_id = BoardID()
        game_id = GameID()

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        updated_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Updated Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=False,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        mock_board_service.get_by_id_or_raise.return_value = existing_board
        mock_board_service.update_board.return_value = updated_board
        mock_board_ratio_config_service.get_by_board_id.return_value = None

        response = await mock_client_no_db.patch(
            f"/boards/{board_id}",
            json={
                "name": "Updated Speed Run Board",
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Speed Run Board"
        assert data["is_active"] is False
        assert data["icon"] == "trophy"

    async def test_update_board_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test updating a non-existent board returns 404."""
        board_id = BoardID()
        mock_board_service.get_by_id_or_raise.side_effect = EntityNotFoundError(
            "Board", str(board_id)
        )

        response = await mock_client_no_db.patch(
            f"/boards/{board_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_soft_delete_board(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test soft-deleting a board via API."""
        account_id = admin_auth.account_id
        board_id = BoardID()
        game_id = GameID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        deleted_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            deleted_at=datetime.now(UTC),
        )

        mock_board_service.get_by_id_or_raise.return_value = board
        mock_board_service.soft_delete.return_value = deleted_board

        # Soft-delete
        response = await mock_client_no_db.patch(
            f"/boards/{board_id}",
            json={"deleted": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(board_id)

        # Verify get raises EntityNotFoundError after delete
        mock_board_service.get_by_id_or_raise.side_effect = EntityNotFoundError(
            "Board", str(board_id)
        )
        get_response = await mock_client_no_db.get(f"/boards/{board_id}")
        assert get_response.status_code == 404

    async def test_list_boards_excludes_deleted(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that list endpoint excludes soft-deleted boards."""
        account_id = admin_auth.account_id
        game_id = GameID()

        # Only the non-deleted board is in the result
        board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            slug="board-two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(f"/boards?account_id={account_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Board Two"

    async def test_create_board_with_custom_slug(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with a custom slug."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="custom-speedrun-slug",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Speed Run Board",
                "slug": "custom-speedrun-slug",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "custom-speedrun-slug"
        assert data["name"] == "Speed Run Board"

    async def test_create_board_auto_generates_slug_when_not_provided(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test that slug is auto-generated from name when not provided."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="My Awesome Board",
            slug="my-awesome-board",
            icon="trophy",
            short_code="MAB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "My Awesome Board",
                "icon": "trophy",
                "short_code": "MAB2025",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-awesome-board"
        assert data["name"] == "My Awesome Board"

    async def test_create_board_with_invalid_slug_format(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with invalid slug format returns 400."""
        account_id = admin_auth.account_id
        game_id = GameID()

        # Mock service raises ValueError for invalid slug (domain validation)
        mock_board_service.create_board.side_effect = ValueError(
            "Board slug must be lowercase alphanumeric with hyphens"
        )

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Invalid Slug Board",
                "slug": "Invalid_Slug!",
                "icon": "trophy",
                "short_code": "ISB2025",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )

        # Domain validation error returns 400
        assert response.status_code == 400
        error_data = response.json()
        assert "slug" in error_data["error"].lower()

    async def test_create_board_with_duplicate_slug_fails(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating boards with duplicate slug in same account+game fails."""
        account_id = admin_auth.account_id
        game_id = GameID()

        # First board succeeds
        first_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="First Board",
            slug="my-unique-slug",
            icon="trophy",
            short_code="FIRST",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.create_board.return_value = first_board

        response1 = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "First Board",
                "slug": "my-unique-slug",
                "icon": "trophy",
                "short_code": "FIRST",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )
        assert response1.status_code == 201

        # Second board fails (duplicate slug)
        mock_board_service.create_board.side_effect = ValueError("Slug already exists")

        response2 = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Second Board",
                "slug": "my-unique-slug",
                "icon": "star",
                "short_code": "SECOND",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
        )

        assert response2.status_code == 400

    async def test_superadmin_list_boards_without_account_id_returns_all(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that superadmin can list boards WITHOUT account_id and sees all accounts."""
        account1_id = AccountID()
        account2_id = AccountID()
        game1_id = GameID()
        game2_id = GameID()

        board1 = Board(
            id=BoardID(),
            account_id=account1_id,
            game_id=game1_id,
            name="Board from Account 1",
            slug="board-from-account-1",
            icon="trophy",
            short_code="BRD1A1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = Board(
            id=BoardID(),
            account_id=account2_id,
            game_id=game2_id,
            name="Board from Account 2",
            slug="board-from-account-2",
            icon="star",
            short_code="BRD2A2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board1, board2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get("/boards")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        board_names = {b["name"] for b in data["data"]}
        assert "Board from Account 1" in board_names
        assert "Board from Account 2" in board_names

    async def test_create_board_with_description(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test creating a board with description via API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SRDAPI",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            description="Complete the level as fast as possible",
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SRDAPI",
                "unit": "seconds",
                "description": "Complete the level as fast as possible",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Speed Run Board"
        assert data["description"] == "Complete the level as fast as possible"

    async def test_update_board_description(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
    ):
        """Test updating a board's description via API."""
        account_id = admin_auth.account_id
        board_id = BoardID()
        game_id = GameID()

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Board to Update",
            slug="board-to-update",
            icon="trophy",
            short_code="UPDDSC",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        updated_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Board to Update",
            slug="board-to-update",
            icon="trophy",
            short_code="UPDDSC",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            description="A brand new description",
        )

        mock_board_service.get_by_id_or_raise.return_value = existing_board
        mock_board_service.update_board.return_value = updated_board
        mock_board_ratio_config_service.get_by_board_id.return_value = None

        update_response = await mock_client_no_db.patch(
            f"/boards/{board_id}",
            json={"description": "A brand new description"},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["description"] == "A brand new description"

    async def test_board_description_defaults_to_none(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_board_ratio_config_service,
        mock_board_hooks,
    ):
        """Test that description defaults to None when not provided via API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        created_board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Simple Board",
            slug="simple-board",
            icon="star",
            short_code="SMPBRD",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            description=None,
        )
        mock_board_service.create_board.return_value = created_board

        response = await mock_client_no_db.post(
            "/boards",
            json={
                "account_id": str(account_id),
                "game_id": str(game_id),
                "name": "Simple Board",
                "icon": "star",
                "short_code": "SMPBRD",
                "unit": "points",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None

    async def test_list_boards_by_slug_via_admin_api(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test listing boards filtered by slug via admin API."""
        account_id = admin_auth.account_id
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )
        mock_game_service.get_game_by_slug.return_value = game

        board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Weekly Challenge",
            slug="weekly",
            short_code="WEEK1",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get("/boards?game_slug=test-game&slug=weekly")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["slug"] == "weekly"
        assert data["data"][0]["name"] == "Weekly Challenge"

    async def test_list_boards_by_slug_requires_game_slug(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that filtering by slug without game_slug returns 400."""
        account_id = admin_auth.account_id

        response = await mock_client_no_db.get(f"/boards?account_id={account_id}&slug=weekly")

        assert response.status_code == 400
        assert "game_id" in response.json()["error"].lower()

    async def test_list_boards_by_slug_returns_multiple_for_admin(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that admin can see multiple boards with same slug (active + inactive)."""
        account_id = admin_auth.account_id
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )
        mock_game_service.get_game_by_slug.return_value = game

        board1 = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Week 1",
            slug="weekly",
            short_code="WEEK1",
            is_active=False,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Week 2",
            slug="weekly",
            short_code="WEEK2",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board1, board2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get("/boards?game_slug=test-game&slug=weekly")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        names = {b["name"] for b in data["data"]}
        assert "Week 1" in names
        assert "Week 2" in names

    async def test_list_boards_by_slug_admin_with_is_active_filter(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_game_service,
    ):
        """Test that admin can filter by slug AND is_active to get single result."""
        account_id = admin_auth.account_id
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )
        mock_game_service.get_game_by_slug.return_value = game

        # Only return the active board
        board = Board(
            id=BoardID(),
            account_id=account_id,
            game_id=game_id,
            name="Week 2 (Current)",
            slug="weekly",
            short_code="WEEK2",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        result = PaginatedResult(
            items=[board],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_board_service.list_boards.return_value = result

        response = await mock_client_no_db.get(
            "/boards?game_slug=test-game&slug=weekly&is_active=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Week 2 (Current)"
        assert data["data"][0]["is_active"] is True
