"""Tests for ScoreEventORM model and ScoreEventRepository conversions."""

from datetime import UTC, datetime

import pytest

from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.scores.adapters.orm import ScoreEventORM
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.repositories import ScoreEventRepository


@pytest.mark.asyncio
class TestScoreEventORM:
    """Tests for ScoreEventORM model."""

    async def test_create_score_event_orm(self, db_session, board_orm, identity_orm):
        """Test creating a ScoreEventORM instance."""
        now = datetime.now(UTC)

        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 1000},
            is_test=False,
            timezone="America/New_York",
            country="US",
            city="New York",
            created_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.id is not None
        assert orm.account_id == board_orm.account_id
        assert orm.game_id == board_orm.game_id
        assert orm.board_id == board_orm.id
        assert orm.identity_id == identity_orm.id
        assert orm.event_payload == {"value": 1000}
        assert orm.is_test is False
        assert orm.timezone == "America/New_York"
        assert orm.country == "US"
        assert orm.city == "New York"
        assert orm.created_at == now

    async def test_score_event_orm_has_no_updated_at(self, db_session, board_orm, identity_orm):
        """Test that ScoreEventORM does not have updated_at column (immutable)."""
        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 100},
            is_test=False,
        )

        db_session.add(orm)
        await db_session.commit()

        # ScoreEventORM should NOT have updated_at column
        assert not hasattr(orm, "updated_at") or getattr(orm, "updated_at", None) is None

    async def test_score_event_orm_has_no_deleted_at(self, db_session, board_orm, identity_orm):
        """Test that ScoreEventORM does not have deleted_at column (append-only)."""
        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 100},
            is_test=False,
        )

        db_session.add(orm)
        await db_session.commit()

        # ScoreEventORM should NOT have deleted_at column
        assert not hasattr(orm, "deleted_at") or getattr(orm, "deleted_at", None) is None

    async def test_score_event_with_null_geo_fields(self, db_session, board_orm, identity_orm):
        """Test creating ScoreEventORM with null geo fields."""
        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 100},
            is_test=False,
            timezone=None,
            country=None,
            city=None,
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.timezone is None
        assert orm.country is None
        assert orm.city is None

    async def test_complex_event_payload_persistence(self, db_session, board_orm, identity_orm):
        """Test that complex event_payload persists correctly as JSONB."""
        complex_payload = {
            "value": 1000,
            "metadata": {
                "level": 5,
                "character": "warrior",
                "items": ["sword", "shield"],
                "stats": {
                    "health": 100,
                    "mana": 50,
                },
            },
        }

        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload=complex_payload,
            is_test=False,
        )

        db_session.add(orm)
        await db_session.commit()
        await db_session.refresh(orm)

        assert orm.event_payload == complex_payload
        assert orm.event_payload["metadata"]["stats"]["health"] == 100
        assert orm.event_payload["metadata"]["items"] == ["sword", "shield"]


@pytest.mark.asyncio
class TestScoreEventRepositoryConversions:
    """Tests for ScoreEventRepository domain/ORM conversions."""

    async def test_to_domain(self, db_session, board_orm, identity_orm):
        """Test converting ORM to domain entity via repository."""
        now = datetime.now(UTC)
        repo = ScoreEventRepository(db_session)

        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 500},
            is_test=True,
            timezone="Europe/London",
            country="GB",
            city="London",
            created_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        domain = repo._to_domain(orm)

        assert isinstance(domain, ScoreEvent)
        assert domain.id == ScoreEventID(orm.id)
        assert domain.account_id == AccountID(board_orm.account_id)
        assert domain.game_id == GameID(board_orm.game_id)
        assert domain.board_id == BoardID(board_orm.id)
        assert domain.identity_id == IdentityID(identity_orm.id)
        assert domain.event_payload == {"value": 500}
        assert domain.is_test is True
        assert domain.timezone == "Europe/London"
        assert domain.country == "GB"
        assert domain.city == "London"
        assert domain.created_at == now

    async def test_to_orm(self, db_session, board_orm, identity_orm):
        """Test converting domain entity to ORM via repository."""
        now = datetime.now(UTC)
        repo = ScoreEventRepository(db_session)

        domain = ScoreEvent(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"delta": 10},
            is_test=False,
            timezone="Asia/Tokyo",
            country="JP",
            city="Tokyo",
            created_at=now,
        )

        orm = repo._to_orm(domain)

        assert orm.id == domain.id.uuid
        assert orm.account_id == board_orm.account_id
        assert orm.game_id == board_orm.game_id
        assert orm.board_id == board_orm.id
        assert orm.identity_id == identity_orm.id
        assert orm.event_payload == {"delta": 10}
        assert orm.is_test is False
        assert orm.timezone == "Asia/Tokyo"
        assert orm.country == "JP"
        assert orm.city == "Tokyo"
        assert orm.created_at == now

    async def test_roundtrip_orm_to_domain(self, db_session, board_orm, identity_orm):
        """Test that converting ORM -> Domain -> ORM preserves all data."""
        now = datetime.now(UTC)
        repo = ScoreEventRepository(db_session)

        original_orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 999, "metadata": {"level": 5}},
            is_test=True,
            timezone="Australia/Sydney",
            country="AU",
            city="Sydney",
            created_at=now,
        )

        db_session.add(original_orm)
        await db_session.commit()

        # ORM -> Domain -> ORM
        domain = repo._to_domain(original_orm)
        new_orm = repo._to_orm(domain)

        assert new_orm.id == original_orm.id
        assert new_orm.account_id == original_orm.account_id
        assert new_orm.game_id == original_orm.game_id
        assert new_orm.board_id == original_orm.board_id
        assert new_orm.identity_id == original_orm.identity_id
        assert new_orm.event_payload == original_orm.event_payload
        assert new_orm.is_test == original_orm.is_test
        assert new_orm.timezone == original_orm.timezone
        assert new_orm.country == original_orm.country
        assert new_orm.city == original_orm.city
        assert new_orm.created_at == original_orm.created_at

    async def test_roundtrip_domain_to_orm(self, db_session, board_orm, identity_orm):
        """Test that converting Domain -> ORM -> Domain preserves all data."""
        now = datetime.now(UTC)
        repo = ScoreEventRepository(db_session)

        original_domain = ScoreEvent(
            account_id=AccountID(board_orm.account_id),
            game_id=GameID(board_orm.game_id),
            board_id=BoardID(board_orm.id),
            identity_id=IdentityID(identity_orm.id),
            event_payload={"value": 12345},
            is_test=False,
            timezone="America/Los_Angeles",
            country="US",
            city="Los Angeles",
            created_at=now,
        )

        # Domain -> ORM -> Domain
        orm = repo._to_orm(original_domain)
        new_domain = repo._to_domain(orm)

        assert new_domain.id == original_domain.id
        assert new_domain.account_id == original_domain.account_id
        assert new_domain.game_id == original_domain.game_id
        assert new_domain.board_id == original_domain.board_id
        assert new_domain.identity_id == original_domain.identity_id
        assert new_domain.event_payload == original_domain.event_payload
        assert new_domain.is_test == original_domain.is_test
        assert new_domain.timezone == original_domain.timezone
        assert new_domain.country == original_domain.country
        assert new_domain.city == original_domain.city
        assert new_domain.created_at == original_domain.created_at

    async def test_to_domain_with_null_geo_fields(self, db_session, board_orm, identity_orm):
        """Test converting ORM to domain with null geo fields."""
        repo = ScoreEventRepository(db_session)

        orm = ScoreEventORM(
            account_id=board_orm.account_id,
            game_id=board_orm.game_id,
            board_id=board_orm.id,
            identity_id=identity_orm.id,
            event_payload={"value": 100},
            is_test=False,
            timezone=None,
            country=None,
            city=None,
        )

        db_session.add(orm)
        await db_session.commit()

        domain = repo._to_domain(orm)
        assert domain.timezone is None
        assert domain.country is None
        assert domain.city is None
