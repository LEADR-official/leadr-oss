"""Tests for BoardTemplate ORM model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from leadr.boards.adapters.orm import BoardTemplateORM
from leadr.boards.domain.board_template import BoardTemplate


class TestBoardTemplateORM:
    """Test suite for BoardTemplate ORM conversions."""

    def test_board_template_orm_to_domain_with_all_fields(self):
        """Test converting ORM model to domain entity with all fields."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        orm = BoardTemplateORM(
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
            deleted_at=None,
        )

        domain = orm.to_domain()

        assert isinstance(domain, BoardTemplate)
        assert domain.id == template_id
        assert domain.account_id == account_id
        assert domain.game_id == game_id
        assert domain.name == "Weekly Speed Run Template"
        assert domain.name_template == "Speed Run Week {week}"
        assert domain.repeat_interval == "7 days"
        assert domain.config == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert domain.config_template == {"tags": ["speedrun", "weekly"]}
        assert domain.next_run_at == next_run_at
        assert domain.is_active is True
        assert domain.created_at == now
        assert domain.updated_at == now
        assert domain.deleted_at is None

    def test_board_template_orm_to_domain_with_minimal_fields(self):
        """Test converting ORM model to domain entity with minimal fields."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=1)

        orm = BoardTemplateORM(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Template",
            name_template=None,
            repeat_interval="1 day",
            config={},
            config_template={},
            next_run_at=next_run_at,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        domain = orm.to_domain()

        assert isinstance(domain, BoardTemplate)
        assert domain.name_template is None
        assert domain.config == {}
        assert domain.config_template == {}

    def test_board_template_domain_to_orm_with_all_fields(self):
        """Test converting domain entity to ORM model with all fields."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)

        domain = BoardTemplate(
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

        orm = BoardTemplateORM.from_domain(domain)

        assert isinstance(orm, BoardTemplateORM)
        assert orm.id == template_id
        assert orm.account_id == account_id
        assert orm.game_id == game_id
        assert orm.name == "Weekly Speed Run Template"
        assert orm.name_template == "Speed Run Week {week}"
        assert orm.repeat_interval == "7 days"
        assert orm.config == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert orm.config_template == {"tags": ["speedrun", "weekly"]}
        assert orm.next_run_at == next_run_at
        assert orm.is_active is True
        assert orm.created_at == now
        assert orm.updated_at == now
        assert orm.deleted_at is None

    def test_board_template_domain_to_orm_with_minimal_fields(self):
        """Test converting domain entity to ORM model with minimal fields."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=1)

        domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Template",
            repeat_interval="1 day",
            next_run_at=next_run_at,
            is_active=False,
            created_at=now,
            updated_at=now,
        )

        orm = BoardTemplateORM.from_domain(domain)

        assert isinstance(orm, BoardTemplateORM)
        assert orm.name_template is None
        assert orm.config == {}
        assert orm.config_template == {}
        assert orm.is_active is False

    def test_board_template_orm_roundtrip_conversion(self):
        """Test that converting ORM -> Domain -> ORM preserves all data."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=30)

        original_orm = BoardTemplateORM(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Monthly Competition Template",
            name_template="Monthly Competition {month}",
            repeat_interval="1 month",
            config={
                "unit": "points",
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            config_template={"tags": ["monthly", "competition"], "icon": "trophy"},
            next_run_at=next_run_at,
            is_active=True,
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
        assert new_orm.config_template == original_orm.config_template
        assert new_orm.next_run_at == original_orm.next_run_at
        assert new_orm.is_active == original_orm.is_active
        assert new_orm.created_at == original_orm.created_at
        assert new_orm.updated_at == original_orm.updated_at
        assert new_orm.deleted_at == original_orm.deleted_at

    def test_board_template_domain_roundtrip_conversion(self):
        """Test that converting Domain -> ORM -> Domain preserves all data."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)
        next_run_at = now + timedelta(days=7)
        deleted_at = now - timedelta(days=1)

        original_domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Deleted Template",
            name_template="Template {date}",
            repeat_interval="7 days",
            config={"test": "value"},
            config_template={"test": "template"},
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
        assert new_domain.config_template == original_domain.config_template
        assert new_domain.next_run_at == original_domain.next_run_at
        assert new_domain.is_active == original_domain.is_active
        assert new_domain.created_at == original_domain.created_at
        assert new_domain.updated_at == original_domain.updated_at
        assert new_domain.deleted_at == original_domain.deleted_at

    def test_board_template_config_jsonb_serialization(self):
        """Test that config dict properly serializes to JSONB."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
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

    def test_board_template_config_template_jsonb_serialization(self):
        """Test that config_template dict properly serializes to JSONB."""
        template_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        # Complex nested config_template
        config_template = {
            "tags": ["tag1", "tag2"],
            "random_config": {"min": 1, "max": 100, "choices": ["a", "b", "c"]},
        }

        domain = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Template",
            repeat_interval="1 day",
            config_template=config_template,
            next_run_at=now + timedelta(days=1),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        orm = BoardTemplateORM.from_domain(domain)
        assert orm.config_template == config_template

        # Verify roundtrip
        domain_back = orm.to_domain()
        assert domain_back.config_template == config_template
