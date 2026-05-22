"""Tests for BaseRepository abstraction."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import UUID4
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.domain.cursor import Cursor
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import PrefixedID
from leadr.common.domain.models import Entity
from leadr.common.domain.pagination import (
    PaginationDirection,
    SortDirection,
    SortField,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.orm import Base
from leadr.common.repositories import BaseRepository


# Test fixtures - Domain Entity
class MockStatus(str, Enum):
    """Test status enum."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MockEntity(Entity):
    """Test domain entity for BaseRepository testing."""

    name: str
    status: MockStatus


# Test fixtures - ORM Model
class MockStatusEnum(str, Enum):
    """Test ORM status enum."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MockEntityORM(Base):
    """Test ORM model for BaseRepository testing."""

    __tablename__ = "test_entities"

    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[MockStatusEnum] = mapped_column(nullable=False)


# Test Repository Implementation
class MockRepository(BaseRepository[MockEntity, MockEntityORM]):
    """Concrete test repository for testing BaseRepository functionality."""

    def _to_domain(self, orm: MockEntityORM) -> MockEntity:
        """Convert ORM to domain entity."""
        return MockEntity(
            id=orm.id,
            name=orm.name,
            status=MockStatus(orm.status.value),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: MockEntity) -> MockEntityORM:
        """Convert domain entity to ORM."""
        orm = MockEntityORM(
            id=entity.id,
            name=entity.name,
            status=MockStatusEnum(entity.status.value),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
        return orm

    def _get_orm_class(self) -> type[MockEntityORM]:
        """Get the ORM model class."""
        return MockEntityORM

    async def filter(  # type: ignore[override] - test repository, intentionally unpaginated
        self, account_id: UUID4 | PrefixedID | None = None, **kwargs: Any
    ) -> list[MockEntity]:
        """Filter test entities.

        This test repository doesn't require account_id (top-level tenant).
        """
        query = select(MockEntityORM).where(MockEntityORM.deleted_at.is_(None))

        if "status" in kwargs and kwargs["status"] is not None:
            status_value = kwargs["status"]
            if isinstance(status_value, MockStatus):
                status_value = status_value.value
            query = query.where(MockEntityORM.status == MockStatusEnum(status_value))

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def filter_paginated(
        self,
        sort_fields: list[SortField],
        cursor: Cursor | None,
        limit: int,
    ) -> PaginatedResult[MockEntity]:
        """Filter with cursor-based pagination, delegating to _execute_paginated_query."""
        query = select(MockEntityORM).where(MockEntityORM.deleted_at.is_(None))
        return await self._execute_paginated_query(query, sort_fields, cursor, limit)


@pytest.mark.asyncio
class TestBaseRepository:
    """Test suite for BaseRepository common functionality."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_table(self, test_engine):
        """Create test table before each test."""
        async with test_engine.begin() as conn:
            await conn.run_sync(MockEntityORM.__table__.create, checkfirst=True)  # type: ignore[attr-defined]

    async def test_create(self, db_session: AsyncSession):
        """Test creating an entity via repository."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        created = await repo.create(entity)

        assert created.id == entity_id
        assert created.name == "Test Entity"
        assert created.status == MockStatus.ACTIVE
        assert created.deleted_at is None

    async def test_get_by_id_found(self, db_session: AsyncSession):
        """Test retrieving an entity by ID when it exists."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)

        # Retrieve it
        retrieved = await repo.get_by_id(entity_id)

        assert retrieved is not None
        assert retrieved.id == entity_id
        assert retrieved.name == "Test Entity"

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent entity returns None."""
        repo = MockRepository(db_session)
        non_existent_id = uuid4()

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_by_id_excludes_deleted_by_default(self, db_session: AsyncSession):
        """Test that get_by_id excludes soft-deleted entities by default."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create and delete entity
        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)
        await repo.delete(entity_id)

        # Should not be found by default
        retrieved = await repo.get_by_id(entity_id)
        assert retrieved is None

    async def test_get_by_id_includes_deleted_when_requested(self, db_session: AsyncSession):
        """Test that get_by_id can include soft-deleted entities."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create and delete entity
        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)
        await repo.delete(entity_id)

        # Should be found when include_deleted=True
        retrieved = await repo.get_by_id(entity_id, include_deleted=True)
        assert retrieved is not None
        assert retrieved.id == entity_id
        assert retrieved.deleted_at is not None

    async def test_update(self, db_session: AsyncSession):
        """Test updating an entity via repository."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)

        # Update it
        entity.name = "Updated Entity"
        entity.status = MockStatus.INACTIVE
        updated = await repo.update(entity)

        assert updated.name == "Updated Entity"
        assert updated.status == MockStatus.INACTIVE

        # Verify in database
        retrieved = await repo.get_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Entity"
        assert retrieved.status == MockStatus.INACTIVE

    async def test_update_non_existent_raises_error(self, db_session: AsyncSession):
        """Test that updating a non-existent entity raises an error."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(EntityNotFoundError):
            await repo.update(entity)

    async def test_delete_soft_deletes(self, db_session: AsyncSession):
        """Test that delete performs soft delete, not hard delete."""
        repo = MockRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = MockEntity(
            id=entity_id,
            name="Test Entity",
            status=MockStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)

        # Delete it
        await repo.delete(entity_id)

        # Should not be found by normal queries
        retrieved = await repo.get_by_id(entity_id)
        assert retrieved is None

        # But should be found with include_deleted=True
        retrieved_with_deleted = await repo.get_by_id(entity_id, include_deleted=True)
        assert retrieved_with_deleted is not None
        assert retrieved_with_deleted.deleted_at is not None

    async def test_delete_non_existent_raises_error(self, db_session: AsyncSession):
        """Test that deleting a non-existent entity raises an error."""
        repo = MockRepository(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError):
            await repo.delete(non_existent_id)

    async def test_filter(self, db_session: AsyncSession):
        """Test filtering entities."""
        repo = MockRepository(db_session)

        # Create multiple entities
        entity1 = MockEntity(
            name="Entity 1",
            status=MockStatus.ACTIVE,
        )
        entity2 = MockEntity(
            name="Entity 2",
            status=MockStatus.INACTIVE,
        )

        await repo.create(entity1)
        await repo.create(entity2)

        # Filter them
        entities = await repo.filter()

        assert len(entities) == 2
        names = {e.name for e in entities}
        assert "Entity 1" in names
        assert "Entity 2" in names

    async def test_filter_excludes_deleted_by_default(self, db_session: AsyncSession):
        """Test that filter() excludes soft-deleted entities by default."""
        repo = MockRepository(db_session)

        # Create entities
        entity1 = MockEntity(
            name="Entity 1",
            status=MockStatus.ACTIVE,
        )
        entity2 = MockEntity(
            name="Entity 2",
            status=MockStatus.INACTIVE,
        )

        await repo.create(entity1)
        await repo.create(entity2)

        # Soft-delete one
        await repo.delete(entity1.id)

        # Filter should only return non-deleted
        entities = await repo.filter()

        assert len(entities) == 1
        assert entities[0].name == "Entity 2"

    async def test_filter_with_status(self, db_session: AsyncSession):
        """Test that filter() can filter by status."""
        repo = MockRepository(db_session)

        # Create entities
        entity1 = MockEntity(
            name="Entity 1",
            status=MockStatus.ACTIVE,
        )
        entity2 = MockEntity(
            name="Entity 2",
            status=MockStatus.INACTIVE,
        )

        await repo.create(entity1)
        await repo.create(entity2)

        # Filter by status
        active_entities = await repo.filter(status=MockStatus.ACTIVE)

        assert len(active_entities) == 1
        assert active_entities[0].name == "Entity 1"
        assert active_entities[0].status == MockStatus.ACTIVE

    # --- Backward cursor pagination tests ---

    @pytest_asyncio.fixture
    async def nine_entities(self, db_session: AsyncSession) -> list[MockEntity]:
        """Create 9 entities with distinct created_at timestamps for stable ordering."""
        repo = MockRepository(db_session)
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        entities = []
        for i in range(9):
            entity = MockEntity(
                name=f"Entity {i + 1}",
                status=MockStatus.ACTIVE,
                created_at=base_time + timedelta(seconds=i),
                updated_at=base_time + timedelta(seconds=i),
            )
            created = await repo.create(entity)
            entities.append(created)
        return entities

    async def test_backward_pagination_returns_previous_page(
        self, db_session: AsyncSession, nine_entities: list[MockEntity]
    ):
        """Paginate forward to page 3, then backward — should get page 2."""
        repo = MockRepository(db_session)
        sort_fields = [
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

        # Page 1 (newest first): entities 9,8,7
        page1 = await repo.filter_paginated(sort_fields, cursor=None, limit=3)
        assert [e.name for e in page1.items] == ["Entity 9", "Entity 8", "Entity 7"]
        assert page1.has_next is True
        assert page1.has_prev is False

        # Page 2: entities 6,5,4
        assert page1.next_position is not None
        fwd_cursor1 = Cursor(
            position=page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor1, limit=3)
        assert [e.name for e in page2.items] == ["Entity 6", "Entity 5", "Entity 4"]
        assert page2.has_next is True
        assert page2.has_prev is True

        # Page 3: entities 3,2,1
        assert page2.next_position is not None
        fwd_cursor2 = Cursor(
            position=page2.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page3 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor2, limit=3)
        assert [e.name for e in page3.items] == ["Entity 3", "Entity 2", "Entity 1"]
        assert page3.has_next is False
        assert page3.has_prev is True

        # Go backward from page 3 — should get page 2
        assert page3.prev_position is not None
        back_cursor = Cursor(
            position=page3.prev_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.BACKWARD,
        )
        prev_page = await repo.filter_paginated(sort_fields, cursor=back_cursor, limit=3)
        assert [e.name for e in prev_page.items] == ["Entity 6", "Entity 5", "Entity 4"]
        assert prev_page.has_next is True
        assert prev_page.has_prev is True

    async def test_backward_pagination_from_page2_returns_page1(
        self, db_session: AsyncSession, nine_entities: list[MockEntity]
    ):
        """Paginate forward to page 2, then backward — should get page 1."""
        repo = MockRepository(db_session)
        sort_fields = [
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

        # Page 1
        page1 = await repo.filter_paginated(sort_fields, cursor=None, limit=3)
        page1_names = [e.name for e in page1.items]

        # Page 2
        assert page1.next_position is not None
        fwd_cursor = Cursor(
            position=page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor, limit=3)

        # Backward from page 2 — should get page 1
        assert page2.prev_position is not None
        back_cursor = Cursor(
            position=page2.prev_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.BACKWARD,
        )
        prev_page = await repo.filter_paginated(sort_fields, cursor=back_cursor, limit=3)
        assert [e.name for e in prev_page.items] == page1_names
        assert prev_page.has_next is True
        assert prev_page.has_prev is False

    async def test_backward_then_forward_roundtrip(
        self, db_session: AsyncSession, nine_entities: list[MockEntity]
    ):
        """Forward to page 2, backward to page 1, forward again — consistent results."""
        repo = MockRepository(db_session)
        sort_fields = [
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

        # Page 1
        page1 = await repo.filter_paginated(sort_fields, cursor=None, limit=3)
        page1_names = [e.name for e in page1.items]

        # Forward to page 2
        assert page1.next_position is not None
        fwd_cursor = Cursor(
            position=page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor, limit=3)
        page2_names = [e.name for e in page2.items]

        # Backward to page 1
        assert page2.prev_position is not None
        back_cursor = Cursor(
            position=page2.prev_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.BACKWARD,
        )
        back_to_page1 = await repo.filter_paginated(sort_fields, cursor=back_cursor, limit=3)
        assert [e.name for e in back_to_page1.items] == page1_names
        assert back_to_page1.has_next is True
        assert back_to_page1.has_prev is False

        # Forward again to page 2
        assert back_to_page1.next_position is not None
        fwd_cursor2 = Cursor(
            position=back_to_page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        back_to_page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor2, limit=3)
        assert [e.name for e in back_to_page2.items] == page2_names
        assert back_to_page2.has_next is True
        assert back_to_page2.has_prev is True

    async def test_backward_pagination_with_asc_sort(
        self, db_session: AsyncSession, nine_entities: list[MockEntity]
    ):
        """Backward pagination works when primary sort is ASC."""
        repo = MockRepository(db_session)
        sort_fields = [
            SortField(name="created_at", direction=SortDirection.ASC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

        # Page 1 (oldest first): entities 1,2,3
        page1 = await repo.filter_paginated(sort_fields, cursor=None, limit=3)
        assert [e.name for e in page1.items] == ["Entity 1", "Entity 2", "Entity 3"]
        assert page1.has_next is True
        assert page1.has_prev is False

        # Page 2: entities 4,5,6
        assert page1.next_position is not None
        fwd_cursor = Cursor(
            position=page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor, limit=3)
        assert [e.name for e in page2.items] == ["Entity 4", "Entity 5", "Entity 6"]
        assert page2.has_next is True
        assert page2.has_prev is True

        # Backward from page 2 — should get page 1
        assert page2.prev_position is not None
        back_cursor = Cursor(
            position=page2.prev_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.BACKWARD,
        )
        prev_page = await repo.filter_paginated(sort_fields, cursor=back_cursor, limit=3)
        assert [e.name for e in prev_page.items] == ["Entity 1", "Entity 2", "Entity 3"]
        assert prev_page.has_next is True
        assert prev_page.has_prev is False

    async def test_backward_to_first_page_has_no_prev(
        self, db_session: AsyncSession, nine_entities: list[MockEntity]
    ):
        """Going backward to the first page sets has_prev=False."""
        repo = MockRepository(db_session)
        sort_fields = [
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

        # Page 1, then forward to page 2
        page1 = await repo.filter_paginated(sort_fields, cursor=None, limit=3)
        assert page1.next_position is not None
        fwd_cursor = Cursor(
            position=page1.next_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        page2 = await repo.filter_paginated(sort_fields, cursor=fwd_cursor, limit=3)

        # Backward to page 1
        assert page2.prev_position is not None
        back_cursor = Cursor(
            position=page2.prev_position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.BACKWARD,
        )
        back_to_page1 = await repo.filter_paginated(sort_fields, cursor=back_cursor, limit=3)

        assert back_to_page1.has_prev is False
        assert back_to_page1.has_next is True
