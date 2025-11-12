"""Tests for board background tasks."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError

from leadr.accounts.services.account_service import AccountService
from leadr.boards.adapters.orm import BoardORM, BoardTemplateORM
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_tasks import expire_boards, process_due_templates
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestProcessDueTemplates:
    """Tests for process_due_templates background task."""

    async def test_process_due_templates_success(self, db_session):
        """Test successfully processing due templates."""
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

        # Create a due template (next_run_at in the past)
        template_service = BoardTemplateService(db_session)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Daily Challenge",
            repeat_interval="1 day",
            next_run_at=past_time,
            is_active=True,
            config={
                "icon": "star",
                "unit": "points",
                "sort_direction": "desc",
                "keep_strategy": "best",
            },
        )

        await db_session.commit()

        # Mock get_db to return our session
        async def mock_get_db():
            yield db_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db):
            # Process templates
            await process_due_templates()

        # Verify board was created
        from sqlalchemy import select

        result = await db_session.execute(
            select(BoardORM).where(
                BoardORM.template_id == template.id,
            )
        )
        boards = result.scalars().all()
        assert len(boards) == 1
        board_orm = boards[0]
        assert board_orm.name == "Daily Challenge"
        assert board_orm.icon == "star"
        assert board_orm.unit == "points"

        # Verify template schedule was advanced
        updated_template = await template_service.get_board_template(template.id)
        assert updated_template is not None
        expected_next_run = past_time + timedelta(days=1)
        assert updated_template.next_run_at == expected_next_run

    async def test_process_due_templates_no_due_templates(self, db_session):
        """Test processing when no templates are due."""
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

        # Create a template that's not due yet (next_run_at in future)
        template_service = BoardTemplateService(db_session)
        future_time = datetime.now(UTC) + timedelta(hours=1)
        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Future Challenge",
            repeat_interval="1 day",
            next_run_at=future_time,
            is_active=True,
        )

        await db_session.commit()

        # Mock get_db
        async def mock_get_db():
            yield db_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db):
            # Process templates - should return early
            await process_due_templates()

        # Verify no board was created
        from sqlalchemy import select

        result = await db_session.execute(
            select(BoardORM).where(
                BoardORM.template_id == template.id,
            )
        )
        boards = result.scalars().all()
        assert len(boards) == 0

    async def test_process_due_templates_database_error_on_query(self, db_session):
        """Test handling database error during template query."""

        async def mock_get_db_with_error():
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(
                side_effect=OperationalError("DB error", {}, Exception())
            )
            yield mock_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db_with_error):
            # Should handle error gracefully and return
            await process_due_templates()
            # No exception should be raised

    async def test_process_due_templates_skips_invalid_template(self, db_session):
        """Test that invalid templates are skipped."""
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

        # Create a valid due template
        template_service = BoardTemplateService(db_session)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        _valid_template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Valid Template",
            repeat_interval="1 day",
            next_run_at=past_time,
            is_active=True,
        )

        await db_session.commit()

        # Mock get_db
        async def mock_get_db():
            yield db_session

        # Mock to_domain to fail on first template, succeed on second
        original_to_domain = BoardTemplateORM.to_domain
        call_count = [0]

        def mock_to_domain(self):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Invalid template")
            return original_to_domain(self)

        with (
            patch("leadr.boards.services.board_tasks.get_db", mock_get_db),
            patch.object(BoardTemplateORM, "to_domain", mock_to_domain),
        ):
            # Process templates - should skip invalid and process valid
            await process_due_templates()

    async def test_process_due_templates_commit_error(self, db_session):
        """Test handling commit error after processing templates."""
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

        # Create a due template
        template_service = BoardTemplateService(db_session)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        _template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Test Template",
            repeat_interval="1 day",
            next_run_at=past_time,
            is_active=True,
        )

        await db_session.commit()

        # Mock session with commit error
        async def mock_get_db_with_commit_error():
            mock_session = MagicMock()
            mock_session.execute = db_session.execute
            mock_session.commit = AsyncMock(
                side_effect=OperationalError("Commit failed", {}, Exception())
            )
            mock_session.rollback = AsyncMock()
            yield mock_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db_with_commit_error):
            # Should handle commit error gracefully
            await process_due_templates()
            # No exception should be raised


@pytest.mark.asyncio
class TestExpireBoards:
    """Tests for expire_boards background task."""

    async def test_expire_boards_success(self, db_session):
        """Test successfully expiring boards."""
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

        # Create an expired board (ends_at in the past)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        board_orm = BoardORM(
            account_id=account.id,
            game_id=game.id,
            name="Expired Board",
            icon="trophy",
            short_code="EXPIRED1",
            unit="points",
            is_active=True,  # Should be set to False
            sort_direction=SortDirection.DESCENDING.value,
            keep_strategy=KeepStrategy.BEST_ONLY.value,
            starts_at=past_time - timedelta(days=1),
            ends_at=past_time,  # Expired
        )
        db_session.add(board_orm)
        await db_session.commit()

        # Mock get_db
        async def mock_get_db():
            yield db_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db):
            # Expire boards
            await expire_boards()

        # Verify board was marked inactive
        await db_session.refresh(board_orm)
        assert board_orm.is_active is False

    async def test_expire_boards_no_expired_boards(self, db_session):
        """Test expiring when no boards are expired."""
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

        # Create an active board that hasn't expired yet
        future_time = datetime.now(UTC) + timedelta(hours=1)
        board_orm = BoardORM(
            account_id=account.id,
            game_id=game.id,
            name="Active Board",
            icon="trophy",
            short_code="ACTIVE01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING.value,
            keep_strategy=KeepStrategy.BEST_ONLY.value,
            starts_at=datetime.now(UTC),
            ends_at=future_time,  # Not expired
        )
        db_session.add(board_orm)
        await db_session.commit()

        # Mock get_db
        async def mock_get_db():
            yield db_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db):
            # Expire boards - should return early
            await expire_boards()

        # Verify board is still active
        await db_session.refresh(board_orm)
        assert board_orm.is_active is True

    async def test_expire_boards_database_error_on_query(self, db_session):
        """Test handling database error during board query."""

        async def mock_get_db_with_error():
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(side_effect=DBAPIError("DB error", {}, Exception()))
            yield mock_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db_with_error):
            # Should handle error gracefully and return
            await expire_boards()
            # No exception should be raised

    async def test_expire_boards_commit_error(self, db_session):
        """Test handling commit error after expiring boards."""
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

        # Create an expired board
        past_time = datetime.now(UTC) - timedelta(hours=1)
        board_orm = BoardORM(
            account_id=account.id,
            game_id=game.id,
            name="Expired Board",
            icon="trophy",
            short_code="EXPIRED2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING.value,
            keep_strategy=KeepStrategy.BEST_ONLY.value,
            starts_at=past_time - timedelta(days=1),
            ends_at=past_time,
        )
        db_session.add(board_orm)
        await db_session.commit()

        # Mock session with commit error
        async def mock_get_db_with_commit_error():
            mock_session = MagicMock()
            mock_session.execute = db_session.execute
            mock_session.commit = AsyncMock(side_effect=DBAPIError("Commit failed", {}, Exception()))
            mock_session.rollback = AsyncMock()
            yield mock_session

        with patch("leadr.boards.services.board_tasks.get_db", mock_get_db_with_commit_error):
            # Should handle commit error gracefully
            await expire_boards()
            # No exception should be raised
