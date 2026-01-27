"""Tests for Game repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, GameID
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


@pytest.mark.asyncio
class TestGameRepository:
    """Test suite for Game repository."""

    async def test_create_game(self, db_session: AsyncSession):
        """Test creating a game via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            steam_app_id="123456",
            created_at=now,
            updated_at=now,
        )

        created = await game_repo.create(game)

        assert created.id == game_id
        assert created.account_id == account_id
        assert created.name == "Super Awesome Game"
        assert created.steam_app_id == "123456"
        assert created.default_board_id is None

    async def test_get_game_by_id(self, db_session: AsyncSession):
        """Test retrieving a game by ID."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Retrieve it
        retrieved = await game_repo.get_by_id(game_id)

        assert retrieved is not None
        assert retrieved.id == game_id
        assert retrieved.name == "Super Awesome Game"

    async def test_get_game_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent game returns None."""
        game_repo = GameRepository(db_session)
        non_existent_id = uuid4()

        result = await game_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_game(self, db_session: AsyncSession):
        """Test updating a game via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Update name
        game.name = "Ultra Awesome Game"
        updated = await game_repo.update(game)

        assert updated.name == "Ultra Awesome Game"

        # Verify in database
        retrieved = await game_repo.get_by_id(game_id)
        assert retrieved is not None
        assert retrieved.name == "Ultra Awesome Game"

    async def test_delete_game(self, db_session: AsyncSession):
        """Test deleting a game via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Delete it
        await game_repo.delete(game_id.uuid)

        # Verify it's gone
        retrieved = await game_repo.get_by_id(game_id)
        assert retrieved is None

    async def test_list_games_by_account(self, db_session: AsyncSession):
        """Test listing all games for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create multiple games
        game_repo = GameRepository(db_session)

        game1 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game One",
            slug="game-one",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game Two",
            slug="game-two",
            created_at=now,
            updated_at=now,
        )

        await game_repo.create(game1)
        await game_repo.create(game2)

        # List games for account
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await game_repo.filter(account_id, pagination=pagination)

        assert len(result.items) == 2
        names = {g.name for g in result.items}
        assert "Game One" in names
        assert "Game Two" in names

    async def test_list_games_filters_by_account(self, db_session: AsyncSession):
        """Test that filter returns only games for specified account."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        account1_id = uuid4()
        account2_id = uuid4()
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(account1_id),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(account2_id),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games for different accounts
        game_repo = GameRepository(db_session)

        game1 = Game(
            id=GameID(uuid4()),
            account_id=AccountID(account1_id),
            name="Account 1 Game",
            slug="account-1-game",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(uuid4()),
            account_id=AccountID(account2_id),
            name="Account 2 Game",
            slug="account-2-game",
            created_at=now,
            updated_at=now,
        )

        await game_repo.create(game1)
        await game_repo.create(game2)

        # List games for account 1
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await game_repo.filter(AccountID(account1_id), pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].name == "Account 1 Game"
        assert result.items[0].account_id == account1_id

    async def test_delete_game_is_soft_delete(self, db_session: AsyncSession):
        """Test that delete performs soft-delete, not hard-delete."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Soft-delete it
        await game_repo.delete(game_id.uuid)

        # Verify it's not returned by normal queries
        retrieved = await game_repo.get_by_id(game_id)
        assert retrieved is None

    async def test_list_games_excludes_deleted(self, db_session: AsyncSession):
        """Test that filter() excludes soft-deleted games."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create games
        game_repo = GameRepository(db_session)

        game1 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game One",
            slug="game-one",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game Two",
            slug="game-two",
            created_at=now,
            updated_at=now,
        )

        await game_repo.create(game1)
        await game_repo.create(game2)

        # Soft-delete one
        await game_repo.delete(game1.id)

        # List should only return non-deleted
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await game_repo.filter(account_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].name == "Game Two"

    async def test_unique_constraint_on_account_and_name(self, db_session: AsyncSession):
        """Test that game names must be unique within an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        game1 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Duplicate Name Game",
            slug="duplicate-name-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)

        # Try to create another game with same name in same account
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Duplicate Name Game",
            slug="duplicate-name-game-2",
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(IntegrityError):
            await game_repo.create(game2)

    async def test_game_name_can_be_duplicated_across_accounts(self, db_session: AsyncSession):
        """Test that game names can be duplicated across different accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        account1_id = uuid4()
        account2_id = uuid4()
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(account1_id),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(account2_id),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games with same name in different accounts
        game_repo = GameRepository(db_session)

        game1 = Game(
            id=GameID(uuid4()),
            account_id=AccountID(account1_id),
            name="Popular Game",
            slug="popular-game",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(uuid4()),
            account_id=AccountID(account2_id),
            name="Popular Game",
            slug="popular-game-2",
            created_at=now,
            updated_at=now,
        )

        # Should not raise IntegrityError
        created1 = await game_repo.create(game1)
        created2 = await game_repo.create(game2)

        assert created1.name == "Popular Game"
        assert created2.name == "Popular Game"
        assert created1.account_id != created2.account_id

    async def test_get_game_by_slug(self, db_session: AsyncSession, test_account: Account):
        """Test getting a game by slug."""
        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        game = Game(
            id=game_id,
            account_id=test_account.id,
            name="My Awesome Game",
            slug="my-awesome-game",
            created_at=now,
            updated_at=now,
        )
        created_game = await game_repo.create(game)

        # Get by slug
        found_game = await game_repo.get_by_slug("my-awesome-game")

        assert found_game is not None
        assert found_game.id == created_game.id
        assert found_game.slug == "my-awesome-game"
        assert found_game.name == "My Awesome Game"

    async def test_get_game_by_slug_not_found(self, db_session: AsyncSession):
        """Test getting a nonexistent game by slug returns None."""
        game_repo = GameRepository(db_session)

        found_game = await game_repo.get_by_slug("nonexistent-game")

        assert found_game is None

    async def test_slug_in_sortable_fields(self, db_session: AsyncSession):
        """Test that slug is in the SORTABLE_FIELDS set."""
        game_repo = GameRepository(db_session)

        assert "slug" in game_repo.SORTABLE_FIELDS

    async def test_slug_globally_unique(self, db_session: AsyncSession, test_account: Account):
        """Test that slugs must be globally unique across all accounts."""
        game_repo = GameRepository(db_session)
        account2_id = AccountID(uuid4())
        now = datetime.now(UTC)

        # Create first game with slug
        game1 = Game(
            id=GameID(uuid4()),
            account_id=test_account.id,
            name="Popular Game 1",
            slug="popular-game-1",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)

        # Try to create second game with same slug in different account
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account2_id,
            name="Popular Game 2",
            slug="popular-game",  # Same slug as game1
            created_at=now,
            updated_at=now,
        )

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            await game_repo.create(game2)
