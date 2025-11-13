"""Tests for Game domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.games.domain.game import Game


class TestGame:
    """Test suite for Game domain model."""

    def test_create_game_with_all_fields(self):
        """Test creating a game with all fields including optional ones."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        default_board_id = uuid4()
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            steam_app_id="123456",
            default_board_id=BoardID(default_board_id),
            created_at=now,
            updated_at=now,
        )

        assert game.id == game_id
        assert game.account_id == account_id
        assert game.name == "Super Awesome Game"
        assert game.steam_app_id == "123456"
        assert game.default_board_id == default_board_id
        assert game.created_at == now
        assert game.updated_at == now

    def test_create_game_with_required_fields_only(self):
        """Test creating a game with only required fields."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Simple Game",
            created_at=now,
            updated_at=now,
        )

        assert game.id == game_id
        assert game.account_id == account_id
        assert game.name == "Simple Game"
        assert game.steam_app_id is None
        assert game.default_board_id is None
        assert game.created_at == now
        assert game.updated_at == now

    def test_game_name_required(self):
        """Test that game name is required."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Game(  # type: ignore[call-arg]
                id=game_id,
                account_id=account_id,
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_game_account_id_required(self):
        """Test that account_id is required."""
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Game(  # type: ignore[call-arg]
                id=game_id,
                name="Game Without Account",
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_game_name_cannot_be_empty(self):
        """Test that game name cannot be empty or whitespace only."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Game(
                id=game_id,
                account_id=account_id,
                name="",
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_game_name_cannot_be_whitespace_only(self):
        """Test that game name cannot be whitespace only."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Game(
                id=game_id,
                account_id=account_id,
                name="   ",
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_game_name_strips_whitespace(self):
        """Test that game name strips leading and trailing whitespace."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="  Padded Name  ",
            created_at=now,
            updated_at=now,
        )

        assert game.name == "Padded Name"

    def test_game_equality_based_on_id(self):
        """Test that game equality is based on ID."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game1 = Game(
            id=game_id,
            account_id=account_id,
            name="Game One",
            created_at=now,
            updated_at=now,
        )

        game2 = Game(
            id=game_id,
            account_id=AccountID(uuid4()),
            name="Game Two",
            created_at=now,
            updated_at=now,
        )

        assert game1 == game2

    def test_game_inequality_different_ids(self):
        """Test that games with different IDs are not equal."""
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game1 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game One",
            created_at=now,
            updated_at=now,
        )

        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game One",
            created_at=now,
            updated_at=now,
        )

        assert game1 != game2

    def test_game_is_hashable(self):
        """Test that game can be used in sets and as dict keys."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Hashable Game",
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        game_set = {game}  # type: ignore[var-annotated]
        assert game in game_set

        # Should work as dict key
        game_dict = {game: "value"}  # type: ignore[dict-item]
        assert game_dict[game] == "value"

    def test_game_immutability_of_id(self):
        """Test that game ID cannot be changed after creation."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Immutable ID Game",
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            game.id = new_id  # type: ignore[misc]

    def test_game_immutability_of_account_id(self):
        """Test that account_id cannot be changed after creation."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Immutable Account Game",
            created_at=now,
            updated_at=now,
        )

        new_account_id = uuid4()

        with pytest.raises(ValidationError):
            game.account_id = new_account_id  # type: ignore[misc]

    def test_game_soft_delete(self):
        """Test that game can be soft-deleted."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Deletable Game",
            created_at=now,
            updated_at=now,
        )

        assert game.is_deleted is False
        assert game.deleted_at is None

        game.soft_delete()

        assert game.is_deleted is True
        assert game.deleted_at is not None

    def test_game_restore(self):
        """Test that soft-deleted game can be restored."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Restorable Game",
            created_at=now,
            updated_at=now,
        )

        game.soft_delete()
        assert game.is_deleted is True

        game.restore()
        assert game.is_deleted is False
        assert game.deleted_at is None
