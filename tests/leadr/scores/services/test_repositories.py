"""Tests for Score repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.repositories import BoardRepository
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
        account_id = uuid4()
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

        # Create user
        user_repo = UserRepository(db_session)
        user_id = uuid4()

        user = User(
            id=user_id,
            account_id=account_id,
            email="player@example.com",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = uuid4()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
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
        score_id = uuid4()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            filter_timezone="America/New_York",
            filter_country="USA",
            filter_city="New York",
            created_at=now,
            updated_at=now,
        )

        created = await score_repo.create(score)

        assert created.id == score_id
        assert created.account_id == account_id
        assert created.game_id == game_id
        assert created.board_id == board_id
        assert created.user_id == user_id
        assert created.player_name == "SpeedRunner99"
        assert created.value == 123.45
        assert created.value_display == "2:03.45"
        assert created.filter_timezone == "America/New_York"
        assert created.filter_country == "USA"
        assert created.filter_city == "New York"

    async def test_get_score_by_id(self, db_session: AsyncSession):
        """Test retrieving a score by ID."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        user_repo = UserRepository(db_session)
        user_id = uuid4()

        user = User(
            id=user_id,
            account_id=account_id,
            email="player@example.com",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        board_repo = BoardRepository(db_session)
        board_id = uuid4()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
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
        score_id = uuid4()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
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
        non_existent_id = uuid4()

        result = await score_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_score(self, db_session: AsyncSession):
        """Test updating a score."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        user_repo = UserRepository(db_session)
        user_id = uuid4()

        user = User(
            id=user_id,
            account_id=account_id,
            email="player@example.com",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        board_repo = BoardRepository(db_session)
        board_id = uuid4()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
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
        score_id = uuid4()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
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

        account1_id = uuid4()
        account1 = Account(
            id=account1_id,
            name="Account 1",
            slug="account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)

        account2_id = uuid4()
        account2 = Account(
            id=account2_id,
            name="Account 2",
            slug="account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account2)

        # Create users for each account
        user_repo = UserRepository(db_session)

        user1_id = uuid4()
        user1 = User(
            id=user1_id,
            account_id=account1_id,
            email="player1@example.com",
            display_name="Player 1",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user1)

        user2_id = uuid4()
        user2 = User(
            id=user2_id,
            account_id=account2_id,
            email="player2@example.com",
            display_name="Player 2",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user2)

        # Create games for each account
        game_repo = GameRepository(db_session)

        game1_id = uuid4()
        game1 = Game(
            id=game1_id,
            account_id=account1_id,
            name="Game 1",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)

        game2_id = uuid4()
        game2 = Game(
            id=game2_id,
            account_id=account2_id,
            name="Game 2",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game2)

        # Create boards for each game
        board_repo = BoardRepository(db_session)

        board1_id = uuid4()
        board1 = Board(
            id=board1_id,
            account_id=account1_id,
            game_id=game1_id,
            name="Board 1",
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

        board2_id = uuid4()
        board2 = Board(
            id=board2_id,
            account_id=account2_id,
            game_id=game2_id,
            name="Board 2",
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
            id=uuid4(),
            account_id=account1_id,
            game_id=game1_id,
            board_id=board1_id,
            user_id=user1_id,
            player_name="Player1Score",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=uuid4(),
            account_id=account2_id,
            game_id=game2_id,
            board_id=board2_id,
            user_id=user2_id,
            player_name="Player2Score",
            value=200.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score2)

        # Filter by account1
        scores = await score_repo.filter(account_id=account1_id)

        assert len(scores) == 1
        assert scores[0].player_name == "Player1Score"
        assert scores[0].account_id == account1_id

    async def test_filter_with_optional_parameters(self, db_session: AsyncSession):
        """Test filtering scores with optional board_id, game_id, user_id."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create two users
        user_repo = UserRepository(db_session)

        user1_id = uuid4()
        user1 = User(
            id=user1_id,
            account_id=account_id,
            email="player1@example.com",
            display_name="Player 1",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user1)

        user2_id = uuid4()
        user2 = User(
            id=user2_id,
            account_id=account_id,
            email="player2@example.com",
            display_name="Player 2",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user2)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create two boards
        board_repo = BoardRepository(db_session)

        board1_id = uuid4()
        board1 = Board(
            id=board1_id,
            account_id=account_id,
            game_id=game_id,
            name="Board 1",
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

        board2_id = uuid4()
        board2 = Board(
            id=board2_id,
            account_id=account_id,
            game_id=game_id,
            name="Board 2",
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
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board1_id,
            user_id=user1_id,
            player_name="Score1",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board1_id,
            user_id=user2_id,
            player_name="Score2",
            value=200.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score2)

        score3 = Score(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board2_id,
            user_id=user1_id,
            player_name="Score3",
            value=300.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score3)

        # Filter by board_id
        scores = await score_repo.filter(account_id=account_id, board_id=board1_id)
        assert len(scores) == 2
        names = {s.player_name for s in scores}
        assert "Score1" in names
        assert "Score2" in names

        # Filter by user_id
        scores = await score_repo.filter(account_id=account_id, user_id=user1_id)
        assert len(scores) == 2
        names = {s.player_name for s in scores}
        assert "Score1" in names
        assert "Score3" in names

        # Filter by board_id and user_id
        scores = await score_repo.filter(
            account_id=account_id, board_id=board1_id, user_id=user1_id
        )
        assert len(scores) == 1
        assert scores[0].player_name == "Score1"

    async def test_filter_excludes_soft_deleted(self, db_session: AsyncSession):
        """Test that filter excludes soft-deleted scores."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        user_repo = UserRepository(db_session)
        user_id = uuid4()

        user = User(
            id=user_id,
            account_id=account_id,
            email="player@example.com",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        board_repo = BoardRepository(db_session)
        board_id = uuid4()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
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
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="Score1",
            value=100.0,
            created_at=now,
            updated_at=now,
        )
        await score_repo.create(score1)

        score2 = Score(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
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
        scores = await score_repo.filter(account_id=account_id)

        assert len(scores) == 1
        assert scores[0].player_name == "Score2"

    async def test_get_by_id_excludes_soft_deleted(self, db_session: AsyncSession):
        """Test that get_by_id excludes soft-deleted scores."""
        # Create supporting entities
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        user_repo = UserRepository(db_session)
        user_id = uuid4()

        user = User(
            id=user_id,
            account_id=account_id,
            email="player@example.com",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        game_repo = GameRepository(db_session)
        game_id = uuid4()

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        board_repo = BoardRepository(db_session)
        board_id = uuid4()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
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
        score_id = uuid4()

        score = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
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
