"""Tests for Score repository services."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.device import Device
from leadr.auth.services.repositories import DeviceRepository
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.repositories import BoardRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.scores.domain.score import Score
from leadr.scores.services.repositories import ScoreRepository


@pytest.mark.asyncio
class TestScoreRepository:
    """Test suite for Score repository."""

    async def test_create_score(self, db_session: AsyncSession):
        """Test creating a score via repository."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create device
        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            # Client's SHA256 device fingerprint
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            timezone="America/New_York",
            country="USA",
            city="New York",
            created_at=now,
            updated_at=now,
        )

        created = await score_repo.create(score)

        assert created.id == score_id
        assert created.account_id == account_id
        assert created.game_id == game_id
        assert created.board_id == board_id
        assert created.device_id == device_id
        assert created.player_name == "SpeedRunner99"
        assert created.value == 123.45
        assert created.value_display == "2:03.45"
        assert created.timezone == "America/New_York"
        assert created.country == "USA"
        assert created.city == "New York"

    async def test_get_score_by_id(self, db_session: AsyncSession):
        """Test retrieving a score by ID."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score)

        # Retrieve it
        retrieved = await score_repo.get_by_id(score_id)

        assert retrieved is not None
        assert retrieved.id == score_id
        assert retrieved.player_name == "SpeedRunner99"
        assert retrieved.value == 123.45

    async def test_get_score_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent score returns None."""
        score_repo = ScoreRepository(db_session)
        non_existent_id = ScoreID()

        result = await score_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_score(self, db_session: AsyncSession):
        """Test updating a score."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score)

        # Update it
        score.player_name = "NewName"
        score.value = 200.0
        updated = await score_repo.update(score)

        assert updated.player_name == "NewName"
        assert updated.value == 200.0

    async def test_filter_by_account_id(self, db_session: AsyncSession):
        """Test filtering scores by account_id."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1_id = AccountID()
        account1 = Account(
            id=account1_id,
            name="Account 1",
            slug="account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)

        account2_id = AccountID()
        account2 = Account(
            id=account2_id,
            name="Account 2",
            slug="account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account2)

        # Create games for each account
        game_repo = GameRepository(db_session)

        game1_id = GameID()
        game1 = Game(
            id=game1_id,
            account_id=account1_id,
            name="Game 1",
            slug="game-1",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)

        game2_id = GameID()
        game2 = Game(
            id=game2_id,
            account_id=account2_id,
            name="Game 2",
            slug="game-2",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game2)

        # Create devices for each account
        device_repo = DeviceRepository(db_session)

        device1_id = DeviceID()
        device1 = Device(
            id=device1_id,
            account_id=account1_id,
            game_id=game1_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device1)

        device2_id = DeviceID()
        device2 = Device(
            id=device2_id,
            account_id=account2_id,
            game_id=game2_id,
            client_fingerprint="f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device2)

        # Create boards for each game
        board_repo = BoardRepository(db_session)

        board1_id = BoardID()
        board1 = Board(
            id=board1_id,
            account_id=account1_id,
            game_id=game1_id,
            name="Board 1",
            slug="board-1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board1)

        board2_id = BoardID()
        board2 = Board(
            id=board2_id,
            account_id=account2_id,
            game_id=game2_id,
            name="Board 2",
            slug="board-2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board2)

        # Create scores for each account
        score_repo = ScoreRepository(db_session)

        score1 = Score(
            id=ScoreID(),
            account_id=account1_id,
            game_id=game1_id,
            board_id=board1_id,
            device_id=device1_id,
            player_name="Player1Score",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=ScoreID(),
            account_id=account2_id,
            game_id=game2_id,
            board_id=board2_id,
            device_id=device2_id,
            player_name="Player2Score",
            value=200.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score2)

        # Filter by account1
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await score_repo.filter(account_id=account1_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].player_name == "Player1Score"
        assert result.items[0].account_id == account1_id

    async def test_filter_with_optional_parameters(self, db_session: AsyncSession):
        """Test filtering scores with optional board_id, game_id, device_id."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create two devices
        device_repo = DeviceRepository(db_session)

        device1_id = DeviceID()
        device1 = Device(
            id=device1_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device1)

        device2_id = DeviceID()
        device2 = Device(
            id=device2_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device2)

        # Create two boards
        board_repo = BoardRepository(db_session)

        board1_id = BoardID()
        board1 = Board(
            id=board1_id,
            account_id=account_id,
            game_id=game_id,
            name="Board 1",
            slug="board-1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board1)

        board2_id = BoardID()
        board2 = Board(
            id=board2_id,
            account_id=account_id,
            game_id=game_id,
            name="Board 2",
            slug="board-2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board2)

        # Create multiple scores
        score_repo = ScoreRepository(db_session)

        score1 = Score(
            id=ScoreID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board1_id,
            device_id=device1_id,
            player_name="Score1",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=ScoreID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board1_id,
            device_id=device2_id,
            player_name="Score2",
            value=200.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score2)

        score3 = Score(
            id=ScoreID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board2_id,
            device_id=device1_id,
            player_name="Score3",
            value=300.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score3)

        # Filter by board_id
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await score_repo.filter(
            account_id=account_id, board_id=board1_id, pagination=pagination
        )
        assert len(result.items) == 2
        names = {s.player_name for s in result.items}
        assert "Score1" in names
        assert "Score2" in names

        # Filter by device_id
        result = await score_repo.filter(
            account_id=account_id, device_id=device1_id, pagination=pagination
        )
        assert len(result.items) == 2
        names = {s.player_name for s in result.items}
        assert "Score1" in names
        assert "Score3" in names

        # Filter by board_id and device_id
        result = await score_repo.filter(
            account_id=account_id, board_id=board1_id, device_id=device1_id, pagination=pagination
        )
        assert len(result.items) == 1
        assert result.items[0].player_name == "Score1"

    async def test_filter_excludes_soft_deleted(self, db_session: AsyncSession):
        """Test that filter excludes soft-deleted scores."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create two scores
        score_repo = ScoreRepository(db_session)

        score1 = Score(
            id=ScoreID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="Score1",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=ScoreID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="Score2",
            value=200.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score2)

        # Soft-delete score1
        score1.soft_delete()
        await score_repo.update(score1)

        # Filter should exclude soft-deleted
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await score_repo.filter(account_id=account_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].player_name == "Score2"

    async def test_get_by_id_excludes_soft_deleted(self, db_session: AsyncSession):
        """Test that get_by_id excludes soft-deleted scores."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score)

        # Soft-delete it
        score.soft_delete()
        await score_repo.update(score)

        # get_by_id should return None for soft-deleted
        result = await score_repo.get_by_id(score_id)
        assert result is None

    async def test_create_score_with_metadata(self, db_session: AsyncSession):
        """Test creating a score with metadata via repository."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create device
        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score with metadata
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()
        metadata = {"level": 5, "character": "Warrior", "loadout": ["sword", "shield"]}

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )

        created = await score_repo.create(score)

        assert created.id == score_id
        assert created.metadata == metadata
        assert created.metadata["level"] == 5  # type: ignore[index]
        assert created.metadata["character"] == "Warrior"  # type: ignore[index]

        # Verify retrieval preserves metadata
        retrieved = await score_repo.get_by_id(score_id)
        assert retrieved is not None
        assert retrieved.metadata == metadata

    async def test_update_score_metadata(self, db_session: AsyncSession):
        """Test updating score metadata via repository."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create device
        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create score with initial metadata
        score_repo = ScoreRepository(db_session)
        score_id = ScoreID()
        initial_metadata = {"level": 1, "character": "Mage"}

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=initial_metadata,
            created_at=now,
            updated_at=now,
        )

        await score_repo.create(score)

        # Update metadata
        new_metadata = {"level": 10, "character": "Warrior", "items": ["sword", "shield", "potion"]}
        score.metadata = new_metadata
        updated = await score_repo.update(score)

        assert updated.metadata == new_metadata
        assert updated.metadata["level"] == 10  # type: ignore[index]

        # Verify retrieval shows updated metadata
        retrieved = await score_repo.get_by_id(score_id)
        assert retrieved is not None
        assert retrieved.metadata == new_metadata

    async def test_filter_around_score_desc_board(self, db_session: AsyncSession):
        """Test filtering scores around a target score with DESC board (higher is better)."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()
        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        # Create DESC board (higher value is better)
        board_repo = BoardRepository(db_session)
        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Highscore Board",
            slug="highscore-board",
            icon="trophy",
            short_code="HSB",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 7 scores with different values
        score_repo = ScoreRepository(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500, 600, 700]:
            score = Score(
                id=ScoreID(),
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name=f"Player{value}",
                value=float(value),
                created_at=now,
                updated_at=now,
            )
            await score_repo.create(score)
            scores.append(score)

        # Target score is value=400 (middle score)
        target_score = scores[3]  # Player400

        # Filter around the target with limit=5 (should get 2 above + target + 2 below)
        from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
        from leadr.common.domain.pagination import SortField

        sort_fields = [
            SortField(name="value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]
        pagination = PaginationParams(cursor=None, limit=5, sort=None)
        pagination.sort_spec = sort_fields

        result = await score_repo.filter(
            account_id=account_id,
            board_id=board_id,
            pagination=pagination,
            around_score=target_score,
        )

        # Should have 5 scores: 600, 500, 400 (target), 300, 200
        assert len(result.items) == 5
        values = [s.value for s in result.items]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

    async def test_filter_around_score_asc_board(self, db_session: AsyncSession):
        """Test filtering scores around a target score with ASC board (lower is better)."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()
        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        # Create ASC board (lower value is better, e.g., time trial)
        board_repo = BoardRepository(db_session)
        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Time Trial Board",
            slug="time-trial-board",
            icon="clock",
            short_code="TTB",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 7 scores with different values (lower is better)
        score_repo = ScoreRepository(db_session)
        scores = []
        for value in [10, 20, 30, 40, 50, 60, 70]:
            score = Score(
                id=ScoreID(),
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name=f"Player{value}",
                value=float(value),
                created_at=now,
                updated_at=now,
            )
            await score_repo.create(score)
            scores.append(score)

        # Target score is value=40 (middle score)
        target_score = scores[3]  # Player40

        # Filter around the target with limit=5
        from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
        from leadr.common.domain.pagination import SortField

        sort_fields = [
            SortField(name="value", direction=PaginationSortDirection.ASC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]
        pagination = PaginationParams(cursor=None, limit=5, sort=None)
        pagination.sort_spec = sort_fields

        result = await score_repo.filter(
            account_id=account_id,
            board_id=board_id,
            pagination=pagination,
            around_score=target_score,
        )

        # Should have 5 scores: 20, 30, 40 (target), 50, 60
        # (lower values are "better"/above in ASC sort)
        assert len(result.items) == 5
        values = [s.value for s in result.items]
        assert values == [20.0, 30.0, 40.0, 50.0, 60.0]

    async def test_filter_around_score_at_top(self, db_session: AsyncSession):
        """Test filtering around a score at the top of the board (no above scores)."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()
        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Highscore Board",
            slug="highscore-board",
            icon="trophy",
            short_code="HSB2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 5 scores
        score_repo = ScoreRepository(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500]:
            score = Score(
                id=ScoreID(),
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name=f"Player{value}",
                value=float(value),
                created_at=now,
                updated_at=now,
            )
            await score_repo.create(score)
            scores.append(score)

        # Target is the top score (500)
        target_score = scores[4]  # Player500

        from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
        from leadr.common.domain.pagination import SortField

        sort_fields = [
            SortField(name="value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]
        pagination = PaginationParams(cursor=None, limit=5, sort=None)
        pagination.sort_spec = sort_fields

        result = await score_repo.filter(
            account_id=account_id,
            board_id=board_id,
            pagination=pagination,
            around_score=target_score,
        )

        # Should have 5 scores: 500 (target), 400, 300, 200, 100
        # No above scores since target is at top
        assert len(result.items) == 5
        values = [s.value for s in result.items]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]

    async def test_filter_around_score_at_bottom(self, db_session: AsyncSession):
        """Test filtering around a score at the bottom of the board (no below scores)."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        device_repo = DeviceRepository(db_session)
        device_id = DeviceID()
        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        await device_repo.create(device)

        board_repo = BoardRepository(db_session)
        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Highscore Board",
            slug="highscore-board",
            icon="trophy",
            short_code="HSB3",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 5 scores
        score_repo = ScoreRepository(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500]:
            score = Score(
                id=ScoreID(),
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name=f"Player{value}",
                value=float(value),
                created_at=now,
                updated_at=now,
            )
            await score_repo.create(score)
            scores.append(score)

        # Target is the bottom score (100)
        target_score = scores[0]  # Player100

        from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
        from leadr.common.domain.pagination import SortField

        sort_fields = [
            SortField(name="value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]
        pagination = PaginationParams(cursor=None, limit=5, sort=None)
        pagination.sort_spec = sort_fields

        result = await score_repo.filter(
            account_id=account_id,
            board_id=board_id,
            pagination=pagination,
            around_score=target_score,
        )

        # Should have 5 scores: 500, 400, 300, 200, 100 (target)
        # No below scores since target is at bottom
        assert len(result.items) == 5
        values = [s.value for s in result.items]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]
