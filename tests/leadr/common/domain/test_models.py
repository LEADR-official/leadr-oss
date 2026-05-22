"""Tests for common domain models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from leadr.common.domain.models import Entity, ImmutableEntity


class TestEntity:
    """Tests for Entity base class."""

    def test_entity_has_soft_delete_fields(self):
        """Test that Entity has deleted_at field."""
        entity = Entity(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )
        assert entity.deleted_at is None

    def test_entity_soft_delete_method(self):
        """Test that Entity has soft_delete() method."""
        entity = Entity(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )

        # Soft delete the entity
        entity.soft_delete()

        assert entity.deleted_at is not None
        assert isinstance(entity.deleted_at, datetime)

    def test_entity_is_deleted_property(self):
        """Test that Entity has is_deleted property."""
        entity = Entity(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )

        # Initially not deleted
        assert entity.is_deleted is False

        # After soft delete
        entity.soft_delete()
        assert entity.is_deleted is True

    def test_soft_delete_idempotent(self):
        """Test that calling soft_delete() multiple times is safe."""
        entity = Entity(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )

        entity.soft_delete()
        first_deleted_at = entity.deleted_at

        # Call again - should not change the timestamp
        entity.soft_delete()
        assert entity.deleted_at == first_deleted_at

    def test_entity_restore_method(self):
        """Test that Entity has restore() method to undelete."""
        entity = Entity(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )

        # Soft delete then restore
        entity.soft_delete()
        assert entity.is_deleted is True

        entity.restore()
        assert entity.is_deleted is False
        assert entity.deleted_at is None


class TestImmutableEntity:
    """Tests for ImmutableEntity base class."""

    def test_auto_generates_id_and_created_at(self):
        """Test that ImmutableEntity auto-generates id and created_at."""
        entity = ImmutableEntity()
        assert entity.id is not None
        assert entity.created_at is not None
        assert isinstance(entity.created_at, datetime)

    def test_id_is_frozen(self):
        """Test that id cannot be reassigned after creation."""
        entity = ImmutableEntity()
        with pytest.raises(Exception):  # noqa: B017
            entity.id = uuid4()

    def test_equality_by_id(self):
        """Test that equality is based on id."""
        shared_id = uuid4()
        entity1 = ImmutableEntity(id=shared_id)
        entity2 = ImmutableEntity(id=shared_id)
        assert entity1 == entity2

    def test_inequality_different_ids(self):
        """Test that entities with different ids are not equal."""
        entity1 = ImmutableEntity()
        entity2 = ImmutableEntity()
        assert entity1 != entity2

    def test_inequality_different_types(self):
        """Test that an entity is not equal to a non-entity."""
        entity = ImmutableEntity()
        assert entity != "not an entity"

    def test_hash_by_id(self):
        """Test that hash is based on id, allowing use in sets."""
        shared_id = uuid4()
        entity1 = ImmutableEntity(id=shared_id)
        entity2 = ImmutableEntity(id=shared_id)
        assert hash(entity1) == hash(entity2)
        assert len({entity1, entity2}) == 1  # type: ignore[reportUnhashable]

    def test_has_no_updated_at(self):
        """Test that ImmutableEntity has no updated_at field."""
        entity = ImmutableEntity()
        assert not hasattr(entity, "updated_at")

    def test_has_no_deleted_at(self):
        """Test that ImmutableEntity has no deleted_at field."""
        entity = ImmutableEntity()
        assert not hasattr(entity, "deleted_at")

    def test_has_no_soft_delete(self):
        """Test that ImmutableEntity has no soft_delete method."""
        entity = ImmutableEntity()
        assert not hasattr(entity, "soft_delete")

    def test_has_no_restore(self):
        """Test that ImmutableEntity has no restore method."""
        entity = ImmutableEntity()
        assert not hasattr(entity, "restore")
