"""Tests for BaseRepository abstraction."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import UUID4
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import PrefixedID
from leadr.common.domain.models import Entity
from leadr.common.orm import Base
from leadr.common.repositories import BaseRepository


# Test fixtures - Domain Entity
class TestStatus(str, Enum):
    """Test status enum."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TestEntity(Entity):
    """Test domain entity for BaseRepository testing."""

    name: str
    status: TestStatus


# Test fixtures - ORM Model
class TestStatusEnum(str, Enum):
    """Test ORM status enum."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TestEntityORM(Base):
    """Test ORM model for BaseRepository testing."""

    __tablename__ = "test_entities"

    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TestStatusEnum] = mapped_column(nullable=False)


# Test Repository Implementation
class TestRepository(BaseRepository[TestEntity, TestEntityORM]):
    """Concrete test repository for testing BaseRepository functionality."""

    def _to_domain(self, orm: TestEntityORM) -> TestEntity:
        """Convert ORM to domain entity."""
        return TestEntity(
            id=orm.id,
            name=orm.name,
            status=TestStatus(orm.status.value),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: TestEntity) -> TestEntityORM:
        """Convert domain entity to ORM."""
        orm = TestEntityORM(
            id=entity.id,
            name=entity.name,
            status=TestStatusEnum(entity.status.value),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
        return orm

    def _get_orm_class(self) -> type[TestEntityORM]:
        """Get the ORM model class."""
        return TestEntityORM

    async def filter(
        self, account_id: UUID4 | PrefixedID | None = None, **kwargs: Any
    ) -> list[TestEntity]:
        """Filter test entities.

        This test repository doesn't require account_id (top-level tenant).
        """
        query = select(TestEntityORM).where(TestEntityORM.deleted_at.is_(None))

        if "status" in kwargs and kwargs["status"] is not None:
            status_value = kwargs["status"]
            if isinstance(status_value, TestStatus):
                status_value = status_value.value
            query = query.where(TestEntityORM.status == TestStatusEnum(status_value))

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]


@pytest.mark.asyncio
class TestBaseRepository:
    """Test suite for BaseRepository common functionality."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_table(self, test_engine):
        """Create test table before each test."""
        async with test_engine.begin() as conn:
            await conn.run_sync(TestEntityORM.__table__.create, checkfirst=True)  # type: ignore[attr-defined]

    async def test_create(self, db_session: AsyncSession):
        """Test creating an entity via repository."""
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        created = await repo.create(entity)

        assert created.id == entity_id
        assert created.name == "Test Entity"
        assert created.status == TestStatus.ACTIVE
        assert created.deleted_at is None

    async def test_get_by_id_found(self, db_session: AsyncSession):
        """Test retrieving an entity by ID when it exists."""
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
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
        repo = TestRepository(db_session)
        non_existent_id = uuid4()

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_by_id_excludes_deleted_by_default(self, db_session: AsyncSession):
        """Test that get_by_id excludes soft-deleted entities by default."""
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create and delete entity
        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
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
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create and delete entity
        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
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
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(entity)

        # Update it
        entity.name = "Updated Entity"
        entity.status = TestStatus.INACTIVE
        updated = await repo.update(entity)

        assert updated.name == "Updated Entity"
        assert updated.status == TestStatus.INACTIVE

        # Verify in database
        retrieved = await repo.get_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Entity"
        assert retrieved.status == TestStatus.INACTIVE

    async def test_update_non_existent_raises_error(self, db_session: AsyncSession):
        """Test that updating a non-existent entity raises an error."""
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(EntityNotFoundError):
            await repo.update(entity)

    async def test_delete_soft_deletes(self, db_session: AsyncSession):
        """Test that delete performs soft delete, not hard delete."""
        repo = TestRepository(db_session)
        entity_id = uuid4()
        now = datetime.now(UTC)

        # Create entity
        entity = TestEntity(
            id=entity_id,
            name="Test Entity",
            status=TestStatus.ACTIVE,
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
        repo = TestRepository(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError):
            await repo.delete(non_existent_id)

    async def test_filter(self, db_session: AsyncSession):
        """Test filtering entities."""
        repo = TestRepository(db_session)

        # Create multiple entities
        entity1 = TestEntity(
            name="Entity 1",
            status=TestStatus.ACTIVE,
        )
        entity2 = TestEntity(
            name="Entity 2",
            status=TestStatus.INACTIVE,
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
        repo = TestRepository(db_session)

        # Create entities
        entity1 = TestEntity(
            name="Entity 1",
            status=TestStatus.ACTIVE,
        )
        entity2 = TestEntity(
            name="Entity 2",
            status=TestStatus.INACTIVE,
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
        repo = TestRepository(db_session)

        # Create entities
        entity1 = TestEntity(
            name="Entity 1",
            status=TestStatus.ACTIVE,
        )
        entity2 = TestEntity(
            name="Entity 2",
            status=TestStatus.INACTIVE,
        )

        await repo.create(entity1)
        await repo.create(entity2)

        # Filter by status
        active_entities = await repo.filter(status=TestStatus.ACTIVE)

        assert len(active_entities) == 1
        assert active_entities[0].name == "Entity 1"
        assert active_entities[0].status == TestStatus.ACTIVE
