"""Tests for BoardTemplate repository services."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.services.repositories import BoardTemplateRepository
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


@pytest.mark.asyncio
class TestBoardTemplateRepository:
    """Test suite for BoardTemplate repository."""

    async def test_create_board_template(self, db_session: AsyncSession):
        """Test creating a board template via repository."""
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

        # Create board template
        template_repo = BoardTemplateRepository(db_session)
        template_id = uuid4()
        next_run_at = now + timedelta(days=7)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Speed Run Template",
            name_template="Speed Run Week {week}",
            repeat_interval="7 days",
            config={"unit": "seconds", "sort_direction": "ASCENDING"},
            config_template={"tags": ["speedrun", "weekly"]},
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        created = await template_repo.create(template)

        assert created.id == template_id
        assert created.account_id == account_id
        assert created.game_id == game_id
        assert created.name == "Weekly Speed Run Template"
        assert created.name_template == "Speed Run Week {week}"
        assert created.repeat_interval == "7 days"
        assert created.config == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert created.config_template == {"tags": ["speedrun", "weekly"]}
        assert created.next_run_at == next_run_at
        assert created.is_active is True

    async def test_get_board_template_by_id(self, db_session: AsyncSession):
        """Test retrieving a board template by ID."""
        # Create account and game
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

        # Create board template
        template_repo = BoardTemplateRepository(db_session)
        template_id = uuid4()
        next_run_at = now + timedelta(days=1)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Daily Template",
            repeat_interval="1 day",
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template)

        # Retrieve by ID
        retrieved = await template_repo.get_by_id(template_id)

        assert retrieved is not None
        assert retrieved.id == template_id
        assert retrieved.name == "Daily Template"
        assert retrieved.repeat_interval == "1 day"

    async def test_get_nonexistent_board_template_returns_none(self, db_session: AsyncSession):
        """Test that getting a nonexistent template returns None."""
        template_repo = BoardTemplateRepository(db_session)
        nonexistent_id = uuid4()

        result = await template_repo.get_by_id(nonexistent_id)

        assert result is None

    async def test_filter_board_templates_by_account(self, db_session: AsyncSession):
        """Test filtering board templates by account_id."""
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

        # Create templates for each account
        template_repo = BoardTemplateRepository(db_session)

        # Two templates for account 1
        template1 = BoardTemplate(
            id=uuid4(),
            account_id=account1_id,
            game_id=game1_id,
            name="Template 1",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template1)

        template2 = BoardTemplate(
            id=uuid4(),
            account_id=account1_id,
            game_id=game1_id,
            name="Template 2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template2)

        # One template for account 2
        template3 = BoardTemplate(
            id=uuid4(),
            account_id=account2_id,
            game_id=game2_id,
            name="Template 3",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template3)

        # Filter by account 1
        account1_templates = await template_repo.filter(account1_id)

        assert len(account1_templates) == 2
        assert all(t.account_id == account1_id for t in account1_templates)

        # Filter by account 2
        account2_templates = await template_repo.filter(account2_id)

        assert len(account2_templates) == 1
        assert account2_templates[0].account_id == account2_id

    async def test_filter_board_templates_by_account_and_game(self, db_session: AsyncSession):
        """Test filtering board templates by account_id and game_id."""
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

        # Create two games
        game_repo = GameRepository(db_session)
        game1_id = uuid4()
        game1 = Game(
            id=game1_id,
            account_id=account_id,
            name="Game 1",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)

        game2_id = uuid4()
        game2 = Game(
            id=game2_id,
            account_id=account_id,
            name="Game 2",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game2)

        # Create templates for each game
        template_repo = BoardTemplateRepository(db_session)

        template1 = BoardTemplate(
            id=uuid4(),
            account_id=account_id,
            game_id=game1_id,
            name="Game 1 Template 1",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template1)

        template2 = BoardTemplate(
            id=uuid4(),
            account_id=account_id,
            game_id=game1_id,
            name="Game 1 Template 2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template2)

        template3 = BoardTemplate(
            id=uuid4(),
            account_id=account_id,
            game_id=game2_id,
            name="Game 2 Template",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template3)

        # Filter by game 1
        game1_templates = await template_repo.filter(account_id, game_id=game1_id)

        assert len(game1_templates) == 2
        assert all(t.game_id == game1_id for t in game1_templates)

        # Filter by game 2
        game2_templates = await template_repo.filter(account_id, game_id=game2_id)

        assert len(game2_templates) == 1
        assert game2_templates[0].game_id == game2_id

    async def test_update_board_template(self, db_session: AsyncSession):
        """Test updating a board template."""
        # Create account and game
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

        # Create template
        template_repo = BoardTemplateRepository(db_session)
        template_id = uuid4()
        next_run_at = now + timedelta(days=7)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Original Template",
            repeat_interval="7 days",
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template)

        # Update template
        template.name = "Updated Template"
        template.repeat_interval = "1 month"
        template.is_active = False

        updated = await template_repo.update(template)

        assert updated.name == "Updated Template"
        assert updated.repeat_interval == "1 month"
        assert updated.is_active is False

        # Verify via get
        retrieved = await template_repo.get_by_id(template_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Template"

    async def test_soft_delete_board_template(self, db_session: AsyncSession):
        """Test soft deleting a board template."""
        # Create account and game
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

        # Create template
        template_repo = BoardTemplateRepository(db_session)
        template_id = uuid4()
        next_run_at = now + timedelta(days=7)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template to Delete",
            repeat_interval="7 days",
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template)

        # Soft delete
        template.soft_delete()
        await template_repo.update(template)

        # Verify not in normal queries
        retrieved = await template_repo.get_by_id(template_id)
        assert retrieved is None

        # Verify not in filter results
        templates = await template_repo.filter(account_id)
        assert len(templates) == 0

    async def test_filter_excludes_soft_deleted_templates(self, db_session: AsyncSession):
        """Test that filter excludes soft-deleted templates."""
        # Create account and game
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

        # Create templates
        template_repo = BoardTemplateRepository(db_session)

        template1 = BoardTemplate(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            name="Active Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template1)

        template2 = BoardTemplate(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            name="Deleted Template",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await template_repo.create(template2)

        # Soft delete template2
        template2.soft_delete()
        await template_repo.update(template2)

        # Filter should only return active template
        templates = await template_repo.filter(account_id)

        assert len(templates) == 1
        assert templates[0].name == "Active Template"
