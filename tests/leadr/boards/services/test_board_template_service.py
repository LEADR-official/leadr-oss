"""Tests for BoardTemplate service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from leadr.boards.domain.board import BoardType, KeepStrategy
from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.games.domain.game import Game


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def service(mock_session):
    """Create BoardTemplateService with mock repository."""
    service = BoardTemplateService(mock_session, repository=MagicMock())
    # Set the session on the repository so GameService can be created
    service.repository.session = mock_session
    return service


@pytest.mark.asyncio
class TestBoardTemplateService:
    """Test suite for BoardTemplate service."""

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template(self, mock_game_service_class, service):
        """Test creating a board template via service."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService to return a game that belongs to the account
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Mock repository.create to return the entity
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create board template
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        template = await service.create_board_template(
            account_id=account_id,
            game_id=game_id,
            name="Weekly Speed Run Template",
            repeat_interval="7 days",
            next_run_at=next_run_at,
            is_active=True,
            slug="weekly-speed-run-template",
        )

        assert template.id is not None
        assert template.account_id == account_id
        assert template.game_id == game_id
        assert template.name == "Weekly Speed Run Template"
        assert template.board_type == BoardType.RUN_IDENTITY
        assert template.repeat_interval == "7 days"
        assert template.next_run_at == next_run_at
        assert template.is_active is True

        # Verify GameService was called to validate game
        mock_game_service.get_by_id_or_raise.assert_called_once_with(game_id)
        service.repository.create.assert_called_once()

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template_with_optional_fields(
        self, mock_game_service_class, service
    ):
        """Test creating a board template with optional fields."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Mock repository
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create template with optional fields
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        template = await service.create_board_template(
            account_id=account_id,
            game_id=game_id,
            name="Weekly Template",
            name_template="Week {week} Competition",
            repeat_interval="7 days",
            config={"unit": "seconds", "sort_direction": "ASCENDING"},
            next_run_at=next_run_at,
            is_active=True,
            slug="weekly-template",
        )

        assert template.name_template == "Week {week} Competition"
        assert template.config == {"unit": "seconds", "sort_direction": "ASCENDING"}

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template_validates_game_belongs_to_account(
        self, mock_game_service_class, service
    ):
        """Test that create_board_template validates the game belongs to the account."""
        account1_id = AccountID(uuid4())
        account2_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService to return a game that belongs to account1
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account1_id, name="Account 1 Game", slug="account-1-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Try to create template for account2 with account1's game
        now = datetime.now(UTC)

        with pytest.raises(ValueError) as exc_info:
            await service.create_board_template(
                account_id=account2_id,
                game_id=game_id,
                name="Invalid Template",
                repeat_interval="7 days",
                slug="invalid-template",
                next_run_at=now + timedelta(days=7),
                is_active=True,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template_raises_error_for_nonexistent_game(
        self, mock_game_service_class, service
    ):
        """Test that create_board_template raises error for non-existent game."""
        account_id = AccountID(uuid4())
        non_existent_game_id = GameID(uuid4())

        # Mock GameService to raise EntityNotFoundError
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(
            side_effect=EntityNotFoundError("Game", str(non_existent_game_id))
        )

        now = datetime.now(UTC)

        with pytest.raises(EntityNotFoundError):
            await service.create_board_template(
                account_id=account_id,
                game_id=non_existent_game_id,
                name="Invalid Template",
                slug="invalid-template",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
            )

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template_validates_name_template_placeholders(
        self, mock_game_service_class, service
    ):
        """Test that create_board_template validates name_template placeholders."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        now = datetime.now(UTC)

        # Try to create template with invalid placeholder
        with pytest.raises(ValueError) as exc_info:
            await service.create_board_template(
                account_id=account_id,
                game_id=game_id,
                name="Invalid Template",
                name_template="Week {invalid_placeholder}",
                repeat_interval="7 days",
                slug="invalid-template",
                next_run_at=now + timedelta(days=7),
                is_active=True,
            )

        assert "invalid placeholder" in str(exc_info.value).lower()

    async def test_get_board_template(self, service):
        """Test retrieving a board template by ID."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        mock_template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Template",
            repeat_interval="1 day",
            slug="test-template",
            next_run_at=now + timedelta(days=1),
            is_active=True,
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_template)

        # Retrieve template
        retrieved = await service.get_board_template(template_id)

        assert retrieved is not None
        assert retrieved.id == template_id
        assert retrieved.name == "Test Template"

        service.repository.get_by_id.assert_called_once_with(template_id)

    async def test_get_nonexistent_board_template_returns_none(self, service):
        """Test that getting a nonexistent template returns None."""
        nonexistent_id = BoardTemplateID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_board_template(nonexistent_id)

        assert result is None
        service.repository.get_by_id.assert_called_once_with(nonexistent_id)

    async def test_list_board_templates_by_account(self, service):
        """Test listing board templates by account."""
        account1_id = AccountID(uuid4())
        game1_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Create mock templates
        template1 = BoardTemplate(
            account_id=account1_id,
            game_id=game1_id,
            name="Template 1",
            repeat_interval="7 days",
            slug="template-1",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )
        template2 = BoardTemplate(
            account_id=account1_id,
            game_id=game1_id,
            name="Template 2",
            slug="template-2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
        )

        # Mock repository.filter to return account1's templates
        mock_result = PaginatedResult(
            items=[template1, template2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List account1 templates
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        account1_result = await service.list_board_templates_by_account(
            account1_id, pagination=pagination
        )

        assert len(account1_result.items) == 2
        assert all(t.account_id == account1_id for t in account1_result.items)

        service.repository.filter.assert_called_once_with(account1_id, pagination=pagination)

    async def test_list_board_templates_by_game(self, service):
        """Test listing board templates by game."""
        account_id = AccountID(uuid4())
        game1_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Create mock templates for game1
        template1 = BoardTemplate(
            account_id=account_id,
            game_id=game1_id,
            name="Game 1 Template 1",
            repeat_interval="7 days",
            slug="game-1-template-1",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )
        template2 = BoardTemplate(
            account_id=account_id,
            game_id=game1_id,
            name="Game 1 Template 2",
            slug="game-1-template-2",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
        )

        # Mock repository.filter
        mock_result = PaginatedResult(
            items=[template1, template2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List game1 templates
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        game1_result = await service.list_board_templates_by_game(
            account_id=account_id, game_id=game1_id, pagination=pagination
        )

        assert len(game1_result.items) == 2
        assert all(t.game_id == game1_id for t in game1_result.items)

        service.repository.filter.assert_called_once_with(
            account_id, game_id=game1_id, pagination=pagination
        )

    async def test_update_board_template(self, service):
        """Test updating a board template."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Create original template
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Original Template",
            repeat_interval="7 days",
            slug="original-template",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=template)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Update template
        new_next_run_at = now + timedelta(days=14)
        updated = await service.update_board_template(
            template_id=template_id,
            name="Updated Template",
            repeat_interval="14 days",
            next_run_at=new_next_run_at,
            is_active=False,
        )

        assert updated.name == "Updated Template"
        assert updated.repeat_interval == "14 days"
        assert updated.next_run_at == new_next_run_at
        assert updated.is_active is False

        service.repository.get_by_id.assert_called_once_with(template_id)
        service.repository.update.assert_called_once()

    async def test_update_board_template_partial_fields(self, service):
        """Test updating only specific fields of a board template."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Create original template
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Original Template",
            repeat_interval="7 days",
            slug="original-template",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=template)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Update only name
        updated = await service.update_board_template(
            template_id=template_id,
            name="New Name",
        )

        assert updated.name == "New Name"
        assert updated.repeat_interval == "7 days"  # Unchanged
        assert updated.is_active is True  # Unchanged

    async def test_update_board_template_validates_name_template(self, service):
        """Test that update_board_template validates name_template placeholders."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Create template
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template",
            repeat_interval="7 days",
            slug="template",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Mock repository
        service.repository.get_by_id = AsyncMock(return_value=template)

        # Try to update with invalid name_template
        with pytest.raises(ValueError) as exc_info:
            await service.update_board_template(
                template_id=template_id,
                name_template="Week {invalid_placeholder}",
            )

        assert "invalid placeholder" in str(exc_info.value).lower()

    async def test_update_nonexistent_board_template_raises_error(self, service):
        """Test that updating a nonexistent template raises error."""
        nonexistent_id = BoardTemplateID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.update_board_template(
                template_id=nonexistent_id,
                name="New Name",
            )

    async def test_soft_delete_board_template(self, service):
        """Test soft deleting a board template."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template to Delete",
            repeat_interval="7 days",
            slug="template-to-delete",
            next_run_at=now + timedelta(days=7),
            is_active=True,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=template)
        service.repository.delete = AsyncMock(return_value=None)

        # Soft delete
        deleted = await service.soft_delete(template_id)

        assert deleted.id == template_id
        # soft_delete returns entity before deletion
        assert deleted.is_deleted is False

        service.repository.get_by_id.assert_called_once_with(template_id)
        service.repository.delete.assert_called_once()

    async def test_advance_template_schedule(self, service):
        """Test advancing a template's schedule."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        original_next_run = now + timedelta(days=7)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Template",
            repeat_interval="7 days",
            next_run_at=original_next_run,
            is_active=True,
            slug="weekly-template",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=template)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Advance schedule
        updated = await service.advance_template_schedule(template_id)

        # Should be advanced by 7 days
        expected_next_run = original_next_run + timedelta(days=7)
        assert updated.next_run_at == expected_next_run
        assert updated.id == template_id
        assert updated.name == "Weekly Template"

        service.repository.get_by_id.assert_called_once_with(template_id)
        service.repository.update.assert_called_once()

    async def test_advance_template_schedule_different_intervals(self, service):
        """Test advancing schedules with different interval types."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Test hourly interval
        hourly_template_id = BoardTemplateID(uuid4())
        hourly_template = BoardTemplate(
            id=hourly_template_id,
            account_id=account_id,
            game_id=game_id,
            name="Hourly Template",
            repeat_interval="1 hour",
            next_run_at=now,
            is_active=True,
            slug="hourly-template",
        )

        service.repository.get_by_id = AsyncMock(return_value=hourly_template)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        advanced_hourly = await service.advance_template_schedule(hourly_template_id)
        assert advanced_hourly.next_run_at == now + timedelta(hours=1)

        # Test weekly interval
        weekly_template_id = BoardTemplateID(uuid4())
        weekly_template = BoardTemplate(
            id=weekly_template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Template",
            repeat_interval="2 weeks",
            next_run_at=now,
            is_active=True,
            slug="weekly-template",
        )

        service.repository.get_by_id = AsyncMock(return_value=weekly_template)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        advanced_weekly = await service.advance_template_schedule(weekly_template_id)
        assert advanced_weekly.next_run_at == now + timedelta(weeks=2)

    async def test_advance_template_schedule_not_found(self, service):
        """Test advancing schedule for non-existent template raises error."""
        non_existent_id = BoardTemplateID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.advance_template_schedule(non_existent_id)

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_unique_series_per_game(self, mock_game_service_class, service):
        """Test that series must be unique per game."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Mock repository.create to raise IntegrityError for duplicate series
        service.repository.create = AsyncMock(
            side_effect=IntegrityError("duplicate key", {}, Exception())
        )

        next_run = datetime.now(UTC) + timedelta(days=1)

        # Try to create template with duplicate series
        with pytest.raises(IntegrityError):
            await service.create_board_template(
                account_id=account_id,
                game_id=game_id,
                name="Second Weekly",
                slug="second-weekly",
                repeat_interval="7 days",
                next_run_at=next_run,
                is_active=True,
                series="weekly",
                config={},
            )

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_same_series_allowed_for_different_games(self, mock_game_service_class, service):
        """Test that the same series can be used across different games."""
        account_id = AccountID(uuid4())
        game1_id = GameID(uuid4())
        game2_id = GameID(uuid4())

        # Mock GameService to return different games
        mock_game_service = mock_game_service_class.return_value
        mock_game1 = Game(account_id=account_id, name="Game One", slug="game-one")
        mock_game2 = Game(account_id=account_id, name="Game Two", slug="game-two")

        async def mock_get_game(game_id):
            if game_id == game1_id:
                return mock_game1
            return mock_game2

        mock_game_service.get_by_id_or_raise = AsyncMock(side_effect=mock_get_game)

        # Mock repository.create to return entities
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        next_run = datetime.now(UTC) + timedelta(days=1)

        # Create template for game1
        template1 = await service.create_board_template(
            account_id=account_id,
            game_id=game1_id,
            name="Game 1 Weekly",
            slug="game1-weekly",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            series="weekly",
            config={},
        )

        # Create template for game2 with same series - should succeed
        template2 = await service.create_board_template(
            account_id=account_id,
            game_id=game2_id,
            name="Game 2 Weekly",
            slug="game2-weekly",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            series="weekly",
            config={},
        )

        assert template1.series == "weekly"
        assert template2.series == "weekly"
        assert template1.game_id != template2.game_id

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_null_series_allowed_multiple_times(self, mock_game_service_class, service):
        """Test that multiple templates can have series=None for the same game."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock GameService
        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Mock repository.create
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        next_run = datetime.now(UTC) + timedelta(days=1)

        # Create first template with series=None
        template1 = await service.create_board_template(
            account_id=account_id,
            game_id=game_id,
            name="Template One",
            slug="template-one",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            config={},
        )

        # Create second template with series=None - should succeed
        template2 = await service.create_board_template(
            account_id=account_id,
            game_id=game_id,
            name="Template Two",
            slug="template-two",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            config={},
        )

        assert template1.series is None
        assert template2.series is None

    @patch("leadr.boards.services.board_template_service.GameService")
    async def test_create_board_template_with_board_type(self, mock_game_service_class, service):
        """Test creating a board template with explicit board_type=RUN_RUNS."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        mock_game_service = mock_game_service_class.return_value
        mock_game = Game(account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        template = await service.create_board_template(
            account_id=account_id,
            game_id=game_id,
            name="Run Runs Template",
            slug="run-runs-template",
            repeat_interval="7 days",
            next_run_at=next_run_at,
            is_active=True,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        assert template.board_type == BoardType.RUN_RUNS
        assert template.keep_strategy == KeepStrategy.NA
