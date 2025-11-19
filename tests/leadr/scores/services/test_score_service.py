"""Tests for Score service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, ScoreID
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        # Try to create score with non-existent board
        score_service = ScoreService(db_session)
        non_existent_board_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=BoardID(non_existent_board_id),
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

        score = await score_service.get_score(ScoreID(non_existent_id))

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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            keep_strategy=KeepStrategy.ALL,  # Use ALL to keep both scores
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

    async def test_update_submission_metadata_with_none_result(self, db_session: AsyncSession):
        """Test that update_submission_metadata returns early if anti_cheat_result is None."""
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
            anti_cheat_enabled=False,  # Disable anti-cheat
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        score, anti_cheat_result = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # anti_cheat_result should be None since anti-cheat is disabled
        assert anti_cheat_result is None

        # Call update_submission_metadata with None (should return early)
        await score_service.update_submission_metadata(
            saved_score=score,
            device_id=device.id,
            board_id=board.id,
            anti_cheat_result=None,
        )

        # Verify no submission metadata was created
        from leadr.scores.services.anti_cheat_repositories import (
            ScoreSubmissionMetaRepository,
        )

        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta = await meta_repo.get_by_device_and_board(device.id, board.id)
        assert meta is None

    async def test_create_score_with_metadata(self, db_session: AsyncSession):
        """Test creating a score with metadata via service."""
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

        # Create score with metadata
        score_service = ScoreService(db_session)
        metadata = {"level": 5, "character": "Warrior", "loadout": ["sword", "shield"]}
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=metadata,
        )

        assert score.metadata == metadata
        assert score.metadata["level"] == 5  # type: ignore[index]
        assert score.metadata["character"] == "Warrior"  # type: ignore[index]

    async def test_update_score_metadata(self, db_session: AsyncSession):
        """Test updating score metadata via service."""
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

        # Create score with initial metadata
        score_service = ScoreService(db_session)
        initial_metadata = {"level": 1, "character": "Mage"}
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=initial_metadata,
        )

        assert score.metadata == initial_metadata

        # Update metadata
        new_metadata = {"level": 10, "character": "Warrior", "items": ["sword", "shield", "potion"]}
        updated = await score_service.update_score(
            score_id=score.id,
            metadata=new_metadata,
        )

        assert updated.metadata == new_metadata
        assert updated.metadata["level"] == 10  # type: ignore[index]

    async def test_keep_strategy_all_keeps_all_scores(self, db_session: AsyncSession):
        """Test that ALL strategy keeps all scores from the same device."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        )

        # Create board with ALL strategy
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="All Scores Board",
            icon="trophy",
            short_code="ALL1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create multiple scores from the same device
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=200.0,
        )
        score3, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=150.0,
        )

        # Verify all scores were saved
        assert score1.id is not None
        assert score2.id is not None
        assert score3.id is not None
        assert score1.id != score2.id
        assert score2.id != score3.id

        # List scores for this board and device - should get all 3
        all_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )

        assert len(all_scores) == 3
        values = {s.value for s in all_scores}
        assert values == {100.0, 200.0, 150.0}

    async def test_keep_strategy_first_only_keeps_first_score(self, db_session: AsyncSession):
        """Test that FIRST_ONLY strategy keeps only the first score from a device."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        )

        # Create board with FIRST_ONLY strategy
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="First Only Board",
            icon="medal",
            short_code="FIRST1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.FIRST_ONLY,
        )

        # Create first score
        score_service = ScoreService(db_session)
        first_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        assert first_score.id is not None
        assert first_score.value == 100.0

        # Try to create second score from same device
        returned_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=200.0,
        )

        # Should return the first score, not save the new one
        assert returned_score.id == first_score.id
        assert returned_score.value == 100.0

        # Verify only one score exists in DB
        all_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )

        assert len(all_scores) == 1
        assert all_scores[0].id == first_score.id
        assert all_scores[0].value == 100.0

    async def test_keep_strategy_first_only_allows_different_devices(
        self, db_session: AsyncSession
    ):
        """Test that FIRST_ONLY allows scores from different devices."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89",
        )

        # Create board with FIRST_ONLY strategy
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="First Only Board",
            icon="medal",
            short_code="FIRST2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.FIRST_ONLY,
        )

        # Create scores from different devices
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device1.id,
            player_name="Player1",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device2.id,
            player_name="Player2",
            value=200.0,
        )

        # Both scores should be saved (different devices)
        assert score1.id is not None
        assert score2.id is not None
        assert score1.id != score2.id

        # Verify both scores exist in DB
        all_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
        )

        assert len(all_scores) == 2
        values = {s.value for s in all_scores}
        assert values == {100.0, 200.0}

    async def test_keep_strategy_latest_only_keeps_latest_score(self, db_session: AsyncSession):
        """Test that LATEST_ONLY strategy keeps only the latest score, soft-deleting old ones."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
        )

        # Create board with LATEST_ONLY strategy
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Latest Only Board",
            icon="star",
            short_code="LATEST1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.LATEST_ONLY,
        )

        # Create first score
        score_service = ScoreService(db_session)
        first_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        assert first_score.id is not None
        assert first_score.value == 100.0

        # Create second score - should soft-delete first
        second_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=200.0,
        )

        assert second_score.id is not None
        assert second_score.value == 200.0
        assert second_score.id != first_score.id

        # Verify first score is soft-deleted
        first_score_check = await score_service.get_score(first_score.id)
        assert first_score_check is None  # Soft-deleted scores not returned by get

        # Verify only second score is active
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == second_score.id

        # Create third score - should soft-delete second
        third_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=150.0,
        )

        assert third_score.id is not None
        assert third_score.value == 150.0
        assert third_score.id != second_score.id

        # Verify only third score is active
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == third_score.id
        assert active_scores[0].value == 150.0

    async def test_keep_strategy_best_only_ascending_keeps_best_score(
        self, db_session: AsyncSession
    ):
        """Test BEST_ONLY with ASCENDING sort keeps lowest value (better score)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
        )

        # Create board with BEST_ONLY + ASCENDING (lower is better)
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Best Only Board (ASC)",
            icon="trophy",
            short_code="BEST-ASC",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        score_service = ScoreService(db_session)

        # Create first score (100)
        first_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )
        assert first_score.value == 100.0

        # Submit better score (50 < 100) - should save and delete old
        better_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=50.0,
        )
        assert better_score.id is not None
        assert better_score.value == 50.0
        assert better_score.id != first_score.id

        # Verify old score is soft-deleted
        first_check = await score_service.get_score(first_score.id)
        assert first_check is None

        # Verify only better score is active
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == better_score.id
        assert active_scores[0].value == 50.0

        # Submit worse score (150 > 50) - should return existing, not save new
        returned_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=150.0,
        )

        # Should return the existing better score
        assert returned_score.id == better_score.id
        assert returned_score.value == 50.0

        # Verify still only one active score
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == better_score.id

        # Submit equal score (50 == 50) - should return existing, not save new
        equal_returned, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=50.0,
        )
        assert equal_returned.id == better_score.id

        # Still only one score
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1

    async def test_keep_strategy_best_only_descending_keeps_best_score(
        self, db_session: AsyncSession
    ):
        """Test BEST_ONLY with DESCENDING sort keeps highest value (better score)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
        )

        # Create board with BEST_ONLY + DESCENDING (higher is better)
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Best Only Board (DESC)",
            icon="medal",
            short_code="BEST-DESC",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        score_service = ScoreService(db_session)

        # Create first score (100)
        first_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )
        assert first_score.value == 100.0

        # Submit better score (150 > 100) - should save and delete old
        better_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=150.0,
        )
        assert better_score.id is not None
        assert better_score.value == 150.0
        assert better_score.id != first_score.id

        # Verify old score is soft-deleted
        first_check = await score_service.get_score(first_score.id)
        assert first_check is None

        # Verify only better score is active
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == better_score.id
        assert active_scores[0].value == 150.0

        # Submit worse score (50 < 150) - should return existing, not save new
        returned_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=50.0,
        )

        # Should return the existing better score
        assert returned_score.id == better_score.id
        assert returned_score.value == 150.0

        # Verify still only one active score
        active_scores = await score_service.list_scores(
            account_id=account.id,
            board_id=board.id,
            device_id=device.id,
        )
        assert len(active_scores) == 1
        assert active_scores[0].id == better_score.id
