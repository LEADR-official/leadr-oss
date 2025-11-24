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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Weekly Speed Run Template",
            slug="weekly-speedrun",
            name_template="Speed Run Week {week}",
            repeat_interval="7 days",
            config={"unit": "seconds", "sort_direction": "ASCENDING"},
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Simple Template",
            slug="simple-template",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                game_id=GameID(game_id),
                name="Template Without Account",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                name="Template Without Game",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="Template Without Interval",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="Template Without Next Run",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="Template Without Active Status",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="",
                slug="test-slug",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="   ",
                slug="test-slug",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="  Padded Template Name  ",
            slug="padded-template",
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
                id=BoardTemplateID(template_id),
                account_id=AccountID(account_id),
                game_id=GameID(game_id),
                name="Test Template",
                slug="test-template",
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
                    id=BoardTemplateID(template_id),
                    account_id=AccountID(account_id),
                    game_id=GameID(game_id),
                    name="Test Template",
                    slug="test-template",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Test Template",
            slug="test-template",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert template.config == {}
        assert isinstance(template.config, dict)

    def test_board_template_equality_based_on_id(self):
        """Test that template equality is based on ID."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        template1 = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template One",
            slug="template-one",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        template2 = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(uuid4()),
            game_id=GameID(uuid4()),
            name="Template Two",
            slug="template-two",
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
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template One",
            slug="template-one",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        template2 = BoardTemplate(
            id=BoardTemplateID(uuid4()),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template One",
            slug="template-one-2",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Hashable Template",
            slug="hashable-template",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Immutable ID Template",
            slug="immutable-id",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Immutable Account Template",
            slug="immutable-account",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Immutable Game Template",
            slug="immutable-game",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Deletable Template",
            slug="deletable-template",
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
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Restorable Template",
            slug="restorable-template",
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


class TestBoardTemplateGenerateName:
    """Test suite for BoardTemplate.generate_name() method."""

    def test_generate_name_falls_back_to_template_name_when_no_name_template(self):
        """Test that generate_name() returns template.name when name_template is None."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Fallback Name",
            slug="fallback-name",
            name_template=None,
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        result = template.generate_name(timestamp=now, series_value=None)
        assert result == "Fallback Name"

    def test_generate_name_with_year_placeholder(self):
        """Test generate_name() with {year} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Championship {year}",
            repeat_interval="1 year",
            next_run_at=now + timedelta(days=365),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Championship 2025"

    def test_generate_name_with_month_placeholder(self):
        """Test generate_name() with {month} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="High Scores - {month}",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "High Scores - July"

    def test_generate_name_with_month_short_placeholder(self):
        """Test generate_name() with {month_short} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Leaderboard {month_short} {year}",
            repeat_interval="1 month",
            next_run_at=now + timedelta(days=30),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Leaderboard Jul 2025"

    def test_generate_name_with_week_placeholder(self):
        """Test generate_name() with {week} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Week {week} Challenge",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # July 15, 2025 is week 29 of the year (ISO week)
        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Week 29 Challenge"

    def test_generate_name_with_quarter_placeholder(self):
        """Test generate_name() with {quarter} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="{quarter} {year} Rankings",
            repeat_interval="3 months",
            next_run_at=now + timedelta(days=90),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # July is Q3
        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Q3 2025 Rankings"

        # January is Q1
        timestamp = datetime(2025, 1, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Q1 2025 Rankings"

        # December is Q4
        timestamp = datetime(2025, 12, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Q4 2025 Rankings"

    def test_generate_name_with_date_placeholder(self):
        """Test generate_name() with {date} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Daily Challenge {date}",
            repeat_interval="1 day",
            next_run_at=now + timedelta(days=1),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=None)
        assert result == "Daily Challenge 2025-07-15"

    def test_generate_name_with_series_placeholder(self):
        """Test generate_name() with {series} placeholder."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Weekly Challenge {series}",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        result = template.generate_name(timestamp=now, series_value=21)
        assert result == "Weekly Challenge 21"

    def test_generate_name_with_multiple_placeholders(self):
        """Test generate_name() with multiple placeholders."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="{month} {year} - Week {series}",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=3)
        assert result == "July 2025 - Week 3"

    def test_generate_name_with_invalid_placeholder_raises_error(self):
        """Test that generate_name() raises ValueError for invalid placeholders."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Challenge {invalid_placeholder}",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError) as exc_info:
            template.generate_name(timestamp=now, series_value=None)

        assert "invalid" in str(exc_info.value).lower()
        assert "placeholder" in str(exc_info.value).lower()

    def test_generate_name_with_series_placeholder_but_no_series_value(self):
        """Test that generate_name() raises error when {series} used but series_value is None."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template="Weekly Challenge {series}",
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError) as exc_info:
            template.generate_name(timestamp=now, series_value=None)

        assert "series" in str(exc_info.value).lower()

    def test_generate_name_with_all_placeholders(self):
        """Test generate_name() with all supported placeholders."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        template = BoardTemplate(
            id=BoardTemplateID(template_id),
            account_id=AccountID(account_id),
            game_id=GameID(game_id),
            name="Template Name",
            slug="template-name",
            name_template=("{year}/{month}/{month_short}/{week}/{quarter}/{date}/#{series}"),
            repeat_interval="7 days",
            next_run_at=now + timedelta(days=7),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        timestamp = datetime(2025, 7, 15, tzinfo=UTC)
        result = template.generate_name(timestamp=timestamp, series_value=42)
        assert result == "2025/July/Jul/29/Q3/2025-07-15/#42"
