"""Tests for ImmutableBaseRepository abstraction."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import UUID4
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import PrefixedID
from leadr.common.domain.models import ImmutableEntity
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.orm import ImmutableBase
from leadr.common.repositories import ImmutableBaseRepository

# Test fixtures - Domain Entity


class MockImmutableEntity(ImmutableEntity):
    """Test domain entity for ImmutableBaseRepository testing."""

    name: str


# Test fixtures - ORM Model


class MockImmutableEntityORM(ImmutableBase):
    """Test ORM model for ImmutableBaseRepository testing."""

    __tablename__ = "test_immutable_entities"

    name: Mapped[str] = mapped_column(String, nullable=False)


# Test Repository Implementation


class MockImmutableRepository(ImmutableBaseRepository[MockImmutableEntity, MockImmutableEntityORM]):
    """Concrete test repository for testing ImmutableBaseRepository."""

    def _to_domain(self, orm: MockImmutableEntityORM) -> MockImmutableEntity:
        return MockImmutableEntity(
            id=orm.id,
            name=orm.name,
            created_at=orm.created_at,
        )

    def _to_orm(self, entity: MockImmutableEntity) -> MockImmutableEntityORM:
        return MockImmutableEntityORM(
            id=entity.id,
            name=entity.name,
            created_at=entity.created_at,
        )

    def _get_orm_class(self) -> type[MockImmutableEntityORM]:
        return MockImmutableEntityORM

    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[MockImmutableEntity]:
        query = select(MockImmutableEntityORM)
        sort_fields = pagination.sort_spec
        cursor = pagination.decode_cursor()
        return await self._execute_paginated_query(query, sort_fields, cursor, pagination.limit)


@pytest.mark.asyncio
class TestImmutableBaseRepository:
    """Test suite for ImmutableBaseRepository common functionality."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_table(self, test_engine):
        """Create test table before each test."""
        async with test_engine.begin() as conn:
            await conn.run_sync(
                MockImmutableEntityORM.__table__.create,  # type: ignore[attr-defined]
                checkfirst=True,
            )

    async def test_create(self, db_session: AsyncSession):
        """Test creating an immutable entity via repository."""
        repo = MockImmutableRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = MockImmutableEntity(id=entity_id, name="Test Event", created_at=now)
        created = await repo.create(entity)

        assert created.id == entity_id
        assert created.name == "Test Event"

    async def test_get_by_id_found(self, db_session: AsyncSession):
        """Test retrieving an immutable entity by ID when it exists."""
        repo = MockImmutableRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = MockImmutableEntity(id=entity_id, name="Test Event", created_at=now)
        await repo.create(entity)

        retrieved = await repo.get_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.id == entity_id
        assert retrieved.name == "Test Event"

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent immutable entity returns None."""
        repo = MockImmutableRepository(db_session)

        result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_list_all_unfiltered(self, db_session: AsyncSession):
        """Test listing all immutable entities."""
        repo = MockImmutableRepository(db_session)
        now = datetime.now(UTC)

        entity1 = MockImmutableEntity(name="Event 1", created_at=now)
        entity2 = MockImmutableEntity(name="Event 2", created_at=now)
        await repo.create(entity1)
        await repo.create(entity2)

        all_entities = await repo._list_all_unfiltered()
        assert len(all_entities) == 2
        names = {e.name for e in all_entities}
        assert names == {"Event 1", "Event 2"}
