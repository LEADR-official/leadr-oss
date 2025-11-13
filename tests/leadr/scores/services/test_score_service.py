"""Tests for Score service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreService:
    """Test suite for Score service."""

    async def test_create_score(self, db_session: AsyncSession):
        """Test creating a score via service."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        assert score.id is not None
        assert score.account_id == account.id
        assert score.game_id == game.id
        assert score.board_id == board.id
        assert score.device_id == device.id
        assert score.player_name == "SpeedRunner99"
        assert score.value == 123.45

    async def test_create_score_with_optional_fields(self, db_session: AsyncSession):
        """Test creating a score with optional fields."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score with optional fields
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            timezone="America/New_York",
            country="USA",
            city="New York",
        )

        assert score.value_display == "2:03.45"
        assert score.timezone == "America/New_York"
        assert score.country == "USA"
        assert score.city == "New York"

    async def test_create_score_validates_board_exists(self, db_session: AsyncSession):
        """Test that create_score validates board exists."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Try to create score with non-existent board
        score_service = ScoreService(db_session)
        non_existent_board_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=non_existent_board_id,
                device_id=device.id,
                player_name="SpeedRunner99",
                value=123.45,
            )

        assert "Board not found" in str(exc_info.value)

    async def test_create_score_validates_board_belongs_to_account(self, db_session: AsyncSession):
        """Test that create_score validates board belongs to account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Account 1",
            slug="account-1",
        )
        account2 = await account_service.create_account(
            name="Account 2",
            slug="account-2",
        )

        # Create games for both accounts
        game_service = GameService(db_session)

        # Create game for account1
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )

        # Create game for account2
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create device for account1/game1
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            device_id="test-device-001",
        )

        # Create board for account2
        board_service = BoardService(db_session)
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Account 2 Board",
            icon="star",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Try to create score for account1 with account2's board
        score_service = ScoreService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await score_service.create_score(
                account_id=account1.id,
                game_id=game1.id,
                board_id=board2.id,
                device_id=device.id,
                player_name="SpeedRunner99",
                value=123.45,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    async def test_create_score_validates_game_matches_board(self, db_session: AsyncSession):
        """Test that create_score validates game_id matches board's game_id."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create two games
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            device_id="test-device-001",
        )

        # Create board for game1
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game1.id,
            name="Game 1 Board",
            icon="trophy",
            short_code="G1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Try to create score with mismatched game_id
        score_service = ScoreService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await score_service.create_score(
                account_id=account.id,
                game_id=game2.id,
                board_id=board.id,
                device_id=device.id,
                player_name="SpeedRunner99",
                value=123.45,
            )

        assert "does not match board" in str(exc_info.value).lower()

    async def test_get_score(self, db_session: AsyncSession):
        """Test retrieving a score by ID via service."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        created_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Retrieve it
        score = await score_service.get_score(created_score.id)

        assert score is not None
        assert score.id == created_score.id
        assert score.player_name == "SpeedRunner99"

    async def test_get_score_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent score returns None."""
        score_service = ScoreService(db_session)
        non_existent_id = uuid4()

        score = await score_service.get_score(non_existent_id)

        assert score is None

    async def test_list_scores_by_account(self, db_session: AsyncSession):
        """Test listing all scores for an account."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create multiple scores
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player2",
            value=200.0,
        )

        # List them
        scores = await score_service.list_scores(account_id=account.id)

        assert len(scores) == 2
        names = {s.player_name for s in scores}
        assert "Player1" in names
        assert "Player2" in names

    async def test_list_scores_filters_by_board(self, db_session: AsyncSession):
        """Test filtering scores by board_id."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores for both boards
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            device_id=device.id,
            player_name="Board1Score",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            device_id=device.id,
            player_name="Board2Score",
            value=200.0,
        )

        # Filter by board1
        scores = await score_service.list_scores(account_id=account.id, board_id=board1.id)

        assert len(scores) == 1
        assert scores[0].player_name == "Board1Score"

    async def test_update_score(self, db_session: AsyncSession):
        """Test updating a score via service."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        created_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Update it
        updated_score = await score_service.update_score(
            score_id=created_score.id,
            player_name="NewName",
            value=200.0,
        )

        assert updated_score.player_name == "NewName"
        assert updated_score.value == 200.0

    async def test_soft_delete_score(self, db_session: AsyncSession):
        """Test soft-deleting a score via service."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        created_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Soft-delete it
        deleted_score = await score_service.soft_delete(created_score.id)

        assert deleted_score.id == created_score.id
        assert deleted_score.is_deleted is False  # Returns entity before deletion

        # Verify it's not returned by get
        score = await score_service.get_score(created_score.id)
        assert score is None
