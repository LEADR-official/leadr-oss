"""Tests for BoardTemplate service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardTemplateService:
    """Test suite for BoardTemplate service."""

    async def test_create_board_template(self, db_session: AsyncSession):
        """Test creating a board template via service."""
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

        # Create board template
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Weekly Speed Run Template",
            repeat_interval="7 days",
            next_run_at=next_run_at,
            is_active=True,
        )

        assert template.id is not None
        assert template.account_id == account.id
        assert template.game_id == game.id
        assert template.name == "Weekly Speed Run Template"
        assert template.repeat_interval == "7 days"
        assert template.next_run_at == next_run_at
        assert template.is_active is True

    async def test_create_board_template_with_optional_fields(self, db_session: AsyncSession):
        """Test creating a board template with optional fields."""
        # Create account and game
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

        # Create template with optional fields
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Weekly Template",
            name_template="Week {week} Competition",
            repeat_interval="7 days",
            config={"unit": "seconds", "sort_direction": "ASCENDING"},
            config_template={"tags": ["weekly", "speedrun"]},
            next_run_at=next_run_at,
            is_active=True,
        )

        assert template.name_template == "Week {week} Competition"
        assert template.config == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert template.config_template == {"tags": ["weekly", "speedrun"]}

    async def test_create_board_template_validates_game_belongs_to_account(
        self, db_session: AsyncSession
    ):
        """Test that create_board_template validates the game belongs to the account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create game for account1
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account1.id,
            name="Account 1 Game",
        )

        # Try to create template for account2 with account1's game
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        with pytest.raises(ValueError) as exc_info:
            await template_service.create_board_template(
                account_id=account2.id,
                game_id=game.id,
                name="Invalid Template",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    async def test_create_board_template_raises_error_for_nonexistent_game(
        self, db_session: AsyncSession
    ):
        """Test that create_board_template raises error for non-existent game."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Try to create template with non-existent game
        template_service = BoardTemplateService(db_session)
        non_existent_game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(EntityNotFoundError):
            await template_service.create_board_template(
                account_id=account.id,
                game_id=non_existent_game_id,
                name="Invalid Template",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
            )

    async def test_get_board_template(self, db_session: AsyncSession):
        """Test retrieving a board template by ID."""
        # Create account and game
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

        # Create template
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        created = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Test Template",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
        )

        # Retrieve template
        retrieved = await template_service.get_board_template(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Template"

    async def test_get_nonexistent_board_template_returns_none(self, db_session: AsyncSession):
        """Test that getting a nonexistent template returns None."""
        template_service = BoardTemplateService(db_session)
        nonexistent_id = uuid4()

        result = await template_service.get_board_template(nonexistent_id)

        assert result is None

    async def test_list_board_templates_by_account(self, db_session: AsyncSession):
        """Test listing board templates by account."""
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

        # Create games for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create templates
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        # Two templates for account1
        await template_service.create_board_template(
            account_id=account1.id,
            game_id=game1.id,
            name="Template 1",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )
        await template_service.create_board_template(
            account_id=account1.id,
            game_id=game1.id,
            name="Template 2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
        )

        # One template for account2
        await template_service.create_board_template(
            account_id=account2.id,
            game_id=game2.id,
            name="Template 3",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
        )

        # List account1 templates
        account1_templates = await template_service.list_board_templates_by_account(account1.id)

        assert len(account1_templates) == 2
        assert all(t.account_id == account1.id for t in account1_templates)

        # List account2 templates
        account2_templates = await template_service.list_board_templates_by_account(account2.id)

        assert len(account2_templates) == 1
        assert account2_templates[0].account_id == account2.id

    async def test_list_board_templates_by_game(self, db_session: AsyncSession):
        """Test listing board templates by game."""
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

        # Create templates
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        await template_service.create_board_template(
            account_id=account.id,
            game_id=game1.id,
            name="Game 1 Template 1",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )
        await template_service.create_board_template(
            account_id=account.id,
            game_id=game1.id,
            name="Game 1 Template 2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
        )
        await template_service.create_board_template(
            account_id=account.id,
            game_id=game2.id,
            name="Game 2 Template",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
        )

        # List game1 templates
        game1_templates = await template_service.list_board_templates_by_game(
            account_id=account.id, game_id=game1.id
        )

        assert len(game1_templates) == 2
        assert all(t.game_id == game1.id for t in game1_templates)

        # List game2 templates
        game2_templates = await template_service.list_board_templates_by_game(
            account_id=account.id, game_id=game2.id
        )

        assert len(game2_templates) == 1
        assert game2_templates[0].game_id == game2.id

    async def test_update_board_template(self, db_session: AsyncSession):
        """Test updating a board template."""
        # Create account and game
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

        # Create template
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Original Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Update template
        new_next_run_at = now + timedelta(days=14)
        updated = await template_service.update_board_template(
            template_id=template.id,
            name="Updated Template",
            repeat_interval="14 days",
            next_run_at=new_next_run_at,
            is_active=False,
        )

        assert updated.name == "Updated Template"
        assert updated.repeat_interval == "14 days"
        assert updated.next_run_at == new_next_run_at
        assert updated.is_active is False

    async def test_update_board_template_partial_fields(self, db_session: AsyncSession):
        """Test updating only specific fields of a board template."""
        # Create account and game
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

        # Create template
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Original Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Update only name
        updated = await template_service.update_board_template(
            template_id=template.id,
            name="New Name",
        )

        assert updated.name == "New Name"
        assert updated.repeat_interval == "7 days"  # Unchanged
        assert updated.is_active is True  # Unchanged

    async def test_update_nonexistent_board_template_raises_error(self, db_session: AsyncSession):
        """Test that updating a nonexistent template raises error."""
        template_service = BoardTemplateService(db_session)
        nonexistent_id = uuid4()

        with pytest.raises(EntityNotFoundError):
            await template_service.update_board_template(
                template_id=nonexistent_id,
                name="New Name",
            )

    async def test_soft_delete_board_template(self, db_session: AsyncSession):
        """Test soft deleting a board template."""
        # Create account and game
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

        # Create template
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Template to Delete",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Soft delete
        deleted = await template_service.soft_delete(template.id)

        assert deleted.id == template.id
        # soft_delete returns entity before deletion
        assert deleted.is_deleted is False

        # Verify not retrievable after deletion
        retrieved = await template_service.get_board_template(template.id)
        assert retrieved is None

        # Verify not in list after deletion
        templates = await template_service.list_board_templates_by_account(account.id)
        assert len(templates) == 0

    async def test_advance_template_schedule(self, db_session: AsyncSession):
        """Test advancing a template's schedule."""
        # Create account and game
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

        # Create template with weekly interval
        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)
        original_next_run = now + timedelta(days=7)

        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Weekly Template",
            repeat_interval="7 days",
            next_run_at=original_next_run,
            is_active=True,
        )

        # Advance schedule
        updated = await template_service.advance_template_schedule(template.id)

        # Should be advanced by 7 days
        expected_next_run = original_next_run + timedelta(days=7)
        assert updated.next_run_at == expected_next_run
        assert updated.id == template.id
        assert updated.name == "Weekly Template"

    async def test_advance_template_schedule_different_intervals(self, db_session: AsyncSession):
        """Test advancing schedules with different interval types."""
        # Create account and game
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

        template_service = BoardTemplateService(db_session)
        now = datetime.now(UTC)

        # Test hourly interval
        hourly_template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Hourly Template",
            repeat_interval="1 hour",
            next_run_at=now,
            is_active=True,
        )

        advanced_hourly = await template_service.advance_template_schedule(hourly_template.id)
        assert advanced_hourly.next_run_at == now + timedelta(hours=1)

        # Test weekly interval
        weekly_template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Weekly Template",
            repeat_interval="2 weeks",
            next_run_at=now,
            is_active=True,
        )

        advanced_weekly = await template_service.advance_template_schedule(weekly_template.id)
        assert advanced_weekly.next_run_at == now + timedelta(weeks=2)

    async def test_advance_template_schedule_not_found(self, db_session: AsyncSession):
        """Test advancing schedule for non-existent template raises error."""
        from leadr.common.domain.exceptions import EntityNotFoundError

        template_service = BoardTemplateService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError):
            await template_service.advance_template_schedule(non_existent_id)
