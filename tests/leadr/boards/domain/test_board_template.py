"""Tests for BoardTemplate domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board_template import BoardTemplate
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID


class TestBoardTemplate:
    """Test suite for BoardTemplate domain model."""

    def test_create_board_template_with_all_fields(self):
        """Test creating a board template with all fields including optional ones."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
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

        assert template.id == template_id
        assert template.account_id == account_id
        assert template.game_id == game_id
        assert template.name == "Weekly Speed Run Template"
        assert template.name_template == "Speed Run Week {week}"
        assert template.repeat_interval == "7 days"
        assert template.config == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert template.config_template == {"tags": ["speedrun", "weekly"]}
        assert template.next_run_at == next_run_at
        assert template.is_active is True
        assert template.created_at == now
        assert template.updated_at == now

    def test_create_board_template_with_required_fields_only(self):
        """Test creating a board template with only required fields."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=1)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Template",
            repeat_interval="1 day",
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.id == template_id
        assert template.account_id == account_id
        assert template.game_id == game_id
        assert template.name == "Simple Template"
        assert template.name_template is None
        assert template.repeat_interval == "1 day"
        assert template.config == {}
        assert template.config_template == {}
        assert template.next_run_at == next_run_at
        assert template.is_active is True
        assert template.created_at == now
        assert template.updated_at == now

    def test_board_template_name_required(self):
        """Test that template name is required."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_board_template_account_id_required(self):
        """Test that account_id is required."""
        template_id = BoardTemplateID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                game_id=game_id,
                name="Template Without Account",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_board_template_game_id_required(self):
        """Test that game_id is required."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                account_id=account_id,
                name="Template Without Game",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_board_template_repeat_interval_required(self):
        """Test that repeat_interval is required."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="Template Without Interval",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "repeat_interval" in str(exc_info.value)

    def test_board_template_next_run_at_required(self):
        """Test that next_run_at is required."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="Template Without Next Run",
                repeat_interval="7 days",
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "next_run_at" in str(exc_info.value)

    def test_board_template_is_active_required(self):
        """Test that is_active is required."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(  # type: ignore[call-arg]
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="Template Without Active Status",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                created_at=now,
                updated_at=now,
            )

        assert "is_active" in str(exc_info.value)

    def test_board_template_name_cannot_be_empty(self):
        """Test that template name cannot be empty or whitespace only."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_template_name_cannot_be_whitespace_only(self):
        """Test that template name cannot be whitespace only."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BoardTemplate(
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="   ",
                repeat_interval="7 days",
                next_run_at=now + timedelta(days=7),
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_template_name_strips_whitespace(self):
        """Test that template name strips leading and trailing whitespace."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="  Padded Template Name  ",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.name == "Padded Template Name"

    def test_board_template_repeat_interval_validates_postgres_syntax(self):
        """Test that repeat_interval validates PostgreSQL interval syntax."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Valid PostgreSQL interval syntax
        valid_intervals = [
            "1 day",
            "7 days",
            "1 week",
            "2 weeks",
            "1 month",
            "3 months",
            "1 year",
            "1 hour",
            "30 minutes",
            "1 day 2 hours",
        ]

        for interval in valid_intervals:
            template = BoardTemplate(
                id=template_id,
                account_id=account_id,
                game_id=game_id,
                name="Test Template",
                repeat_interval=interval,
                next_run_at=now + timedelta(days=1),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            assert template.repeat_interval == interval

    def test_board_template_repeat_interval_rejects_invalid_syntax(self):
        """Test that repeat_interval rejects invalid PostgreSQL syntax."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Invalid interval syntax
        invalid_intervals = [
            "",
            "invalid",
            "1 dayss",  # typo
            "foo bar",
            "123",  # number without unit
        ]

        for interval in invalid_intervals:
            with pytest.raises(ValidationError) as exc_info:
                BoardTemplate(
                    id=template_id,
                    account_id=account_id,
                    game_id=game_id,
                    name="Test Template",
                    repeat_interval=interval,
                    next_run_at=now + timedelta(days=1),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )

            assert "repeat_interval" in str(exc_info.value).lower()

    def test_board_template_config_defaults_to_empty_dict(self):
        """Test that config defaults to empty dict when not provided."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.config == {}
        assert isinstance(template.config, dict)

    def test_board_template_config_template_defaults_to_empty_dict(self):
        """Test that config_template defaults to empty dict when not provided."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.config_template == {}
        assert isinstance(template.config_template, dict)

    def test_board_template_equality_based_on_id(self):
        """Test that template equality is based on ID."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template1 = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template One",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        template2 = BoardTemplate(
            id=template_id,
            account_id=AccountID(uuid4()),
            game_id=GameID(uuid4()),
            name="Template Two",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=False,
            created_at=now,
            updated_at=now,
        )

        assert template1 == template2

    def test_board_template_inequality_different_ids(self):
        """Test that templates with different IDs are not equal."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template1 = BoardTemplate(
            id=BoardTemplateID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Template One",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        template2 = BoardTemplate(
            id=BoardTemplateID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Template One",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template1 != template2

    def test_board_template_is_hashable(self):
        """Test that template can be used in sets and as dict keys."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Hashable Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        template_set = {template}  # type: ignore[var-annotated]
        assert template in template_set

        # Should work as dict key
        template_dict = {template: "value"}  # type: ignore[dict-item]
        assert template_dict[template] == "value"

    def test_board_template_immutability_of_id(self):
        """Test that template ID cannot be changed after creation."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable ID Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            template.id = new_id  # type: ignore[misc]

    def test_board_template_immutability_of_account_id(self):
        """Test that account_id cannot be changed after creation."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Account Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        new_account_id = uuid4()

        with pytest.raises(ValidationError):
            template.account_id = new_account_id  # type: ignore[misc]

    def test_board_template_immutability_of_game_id(self):
        """Test that game_id cannot be changed after creation."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Game Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        new_game_id = uuid4()

        with pytest.raises(ValidationError):
            template.game_id = new_game_id  # type: ignore[misc]

    def test_board_template_soft_delete(self):
        """Test that template can be soft-deleted."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Deletable Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.is_deleted is False
        assert template.deleted_at is None

        template.soft_delete()

        assert template.is_deleted is True
        assert template.deleted_at is not None

    def test_board_template_restore(self):
        """Test that soft-deleted template can be restored."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Restorable Template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        template.soft_delete()
        assert template.is_deleted is True

        template.restore()
        assert template.is_deleted is False
        assert template.deleted_at is None
