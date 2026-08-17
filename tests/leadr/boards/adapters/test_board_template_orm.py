"""Tests for BoardTemplate ORM model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from leadr.boards.adapters.orm import BoardTemplateORM, BoardTypeEnum, KeepStrategyEnum
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_template import BoardTemplate
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID


class TestBoardTemplateORM:
    """Test suite for BoardTemplate ORM conversions."""

    def test_board_template_orm_to_domain_with_all_fields(self):
        """Test converting ORM model to domain entity with all fields."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        orm = BoardTemplateORM(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Speed Run Template",
            slug="weekly-speedrun",
            name_template="Speed Run Week {week}",
            icon="fa-trophy",
            unit="seconds",
            sort_direction="ASCENDING",
            board_type=BoardTypeEnum.RUN_IDENTITY,
            keep_strategy=KeepStrategyEnum.BEST,
            starts_at=now,
            ends_at=now + timedelta(days=30),
            tags=["speedrun", "weekly"],
            repeat_interval="7 days",
            config={"custom": "value"},
            next_run_at=next_run_at,
            is_active=True,
            is_published=True,
            unique_player_names=False,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        domain = orm.to_domain()

        assert isinstance(domain, BoardTemplate)
        assert domain.id == template_id
        assert domain.account_id == account_id
        assert domain.game_id == game_id
        assert domain.name == "Weekly Speed Run Template"
        assert domain.slug == "weekly-speedrun"
        assert domain.name_template == "Speed Run Week {week}"
        assert domain.icon == "fa-trophy"
        assert domain.unit == "seconds"
        assert domain.sort_direction == SortDirection.ASCENDING
        assert domain.board_type == BoardType.RUN_IDENTITY
        assert domain.keep_strategy == KeepStrategy.BEST
        assert domain.starts_at == now
        assert domain.ends_at == now + timedelta(days=30)
        assert domain.tags == ["speedrun", "weekly"]
        assert domain.repeat_interval == "7 days"
        assert domain.config == {"custom": "value"}
        assert domain.next_run_at == next_run_at
        assert domain.is_active is True
        assert domain.is_published is True
        assert domain.created_at == now
        assert domain.updated_at == now
        assert domain.deleted_at is None

    def test_board_template_orm_to_domain_with_minimal_fields(self):
        """Test converting ORM model to domain entity with minimal fields."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=1)

        orm = BoardTemplateORM(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Template",
            slug="simple-template",
            name_template=None,
            icon="fa-crown",
            unit=None,
            sort_direction="DESCENDING",
            board_type=BoardTypeEnum.RUN_IDENTITY,
            keep_strategy=KeepStrategyEnum.BEST,
            starts_at=None,
            ends_at=None,
            tags=[],
            repeat_interval="1 day",
            config={},
            next_run_at=next_run_at,
            is_active=True,
            is_published=True,
            unique_player_names=False,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        domain = orm.to_domain()

        assert isinstance(domain, BoardTemplate)
        assert domain.slug == "simple-template"
        assert domain.name_template is None
        assert domain.icon == "fa-crown"
        assert domain.unit is None
        assert domain.sort_direction == SortDirection.DESCENDING
        assert domain.board_type == BoardType.RUN_IDENTITY
        assert domain.keep_strategy == KeepStrategy.BEST
        assert domain.starts_at is None
        assert domain.ends_at is None
        assert domain.tags == []
        assert domain.config == {}
        assert domain.is_published is True

    def test_board_template_domain_to_orm_with_all_fields(self):
        """Test converting domain entity to ORM model with all fields."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Speed Run Template",
            slug="weekly-speedrun",
            name_template="Speed Run Week {week}",
            icon="fa-trophy",
            unit="seconds",
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            starts_at=now,
            ends_at=now + timedelta(days=30),
            tags=["speedrun", "weekly"],
            repeat_interval="7 days",
            config={"custom": "value"},
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        orm = BoardTemplateORM.from_domain(domain)

        assert isinstance(orm, BoardTemplateORM)
        assert orm.id == template_id
        assert orm.account_id == account_id
        assert orm.game_id == game_id
        assert orm.name == "Weekly Speed Run Template"
        assert orm.slug == "weekly-speedrun"
        assert orm.name_template == "Speed Run Week {week}"
        assert orm.icon == "fa-trophy"
        assert orm.unit == "seconds"
        assert orm.sort_direction == "ASCENDING"
        assert orm.board_type == BoardTypeEnum.RUN_IDENTITY
        assert orm.keep_strategy == KeepStrategyEnum.BEST
        assert orm.starts_at == now
        assert orm.ends_at == now + timedelta(days=30)
        assert orm.tags == ["speedrun", "weekly"]
        assert orm.repeat_interval == "7 days"
        assert orm.config == {"custom": "value"}
        assert orm.next_run_at == next_run_at
        assert orm.is_active is True
        assert orm.created_at == now
        assert orm.updated_at == now
        assert orm.deleted_at is None

    def test_board_template_domain_to_orm_with_minimal_fields(self):
        """Test converting domain entity to ORM model with minimal fields."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=1)

        domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Template",
            slug="simple-template",
            repeat_interval="1 day",
            next_run_at=next_run_at,
            is_active=False,
            created_at=now,
            updated_at=now,
        )

        orm = BoardTemplateORM.from_domain(domain)

        assert isinstance(orm, BoardTemplateORM)
        assert orm.slug == "simple-template"
        assert orm.name_template is None
        assert orm.config == {}
        assert orm.is_active is False

    def test_board_template_orm_roundtrip_conversion(self):
        """Test that converting ORM -> Domain -> ORM preserves all data."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=30)

        original_orm = BoardTemplateORM(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Monthly Competition Template",
            slug="monthly-competition",
            name_template="Monthly Competition {month}",
            icon="fa-crown",
            unit=None,
            sort_direction="DESCENDING",
            board_type=BoardTypeEnum.RUN_IDENTITY,
            keep_strategy=KeepStrategyEnum.BEST,
            starts_at=None,
            ends_at=None,
            tags=["monthly", "competition"],
            repeat_interval="1 month",
            config={
                "unit": "points",
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST",
            },
            next_run_at=next_run_at,
            is_active=True,
            is_published=True,
            unique_player_names=False,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        # ORM -> Domain -> ORM
        domain = original_orm.to_domain()
        new_orm = BoardTemplateORM.from_domain(domain)

        # Verify all fields match
        assert new_orm.id == original_orm.id
        assert new_orm.account_id == original_orm.account_id
        assert new_orm.game_id == original_orm.game_id
        assert new_orm.name == original_orm.name
        assert new_orm.name_template == original_orm.name_template
        assert new_orm.repeat_interval == original_orm.repeat_interval
        assert new_orm.config == original_orm.config
        assert new_orm.next_run_at == original_orm.next_run_at
        assert new_orm.is_active == original_orm.is_active
        assert new_orm.created_at == original_orm.created_at
        assert new_orm.updated_at == original_orm.updated_at
        assert new_orm.deleted_at == original_orm.deleted_at

    def test_board_template_domain_roundtrip_conversion(self):
        """Test that converting Domain -> ORM -> Domain preserves all data."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)
        deleted_at = now - timedelta(days=1)

        original_domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Deleted Template",
            slug="deleted-template",
            name_template="Template {date}",
            repeat_interval="7 days",
            config={"test": "value"},
            next_run_at=next_run_at,
            is_active=False,
            created_at=now,
            updated_at=now,
            deleted_at=deleted_at,
        )

        # Domain -> ORM -> Domain
        orm = BoardTemplateORM.from_domain(original_domain)
        new_domain = orm.to_domain()

        # Verify all fields match
        assert new_domain.id == original_domain.id
        assert new_domain.account_id == original_domain.account_id
        assert new_domain.game_id == original_domain.game_id
        assert new_domain.name == original_domain.name
        assert new_domain.name_template == original_domain.name_template
        assert new_domain.repeat_interval == original_domain.repeat_interval
        assert new_domain.config == original_domain.config
        assert new_domain.next_run_at == original_domain.next_run_at
        assert new_domain.is_active == original_domain.is_active
        assert new_domain.created_at == original_domain.created_at
        assert new_domain.updated_at == original_domain.updated_at
        assert new_domain.deleted_at == original_domain.deleted_at

    def test_board_template_config_jsonb_serialization(self):
        """Test that config dict properly serializes to JSONB."""
        template_id = BoardTemplateID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        # Complex nested config
        config = {
            "unit": "seconds",
            "settings": {"nested": {"value": 123, "enabled": True}},
            "list": [1, 2, 3],
        }

        domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template",
            slug="test-template",
            repeat_interval="1 day",
            config=config,
            next_run_at=now + timedelta(days=1),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        orm = BoardTemplateORM.from_domain(domain)
        assert orm.config == config

        # Verify roundtrip
        domain_back = orm.to_domain()
        assert domain_back.config == config
