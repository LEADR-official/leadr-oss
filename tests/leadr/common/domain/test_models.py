"""Tests for common domain models."""

from datetime import datetime, timezone

import pytest

from leadr.common.domain.models import Entity, EntityID


class TestEntityID:
    """Tests for EntityID value object."""

    def test_generate_creates_unique_ids(self):
        """Test that generate() creates unique IDs."""
        id1 = EntityID.generate()
        id2 = EntityID.generate()
        assert id1 != id2

    def test_from_string_creates_entity_id(self):
        """Test that from_string() creates EntityID from UUID string."""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        entity_id = EntityID.from_string(uuid_str)
        assert str(entity_id) == uuid_str

    def test_entity_id_equality(self):
        """Test that EntityIDs with same UUID are equal."""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        id1 = EntityID.from_string(uuid_str)
        id2 = EntityID.from_string(uuid_str)
        assert id1 == id2

    def test_entity_id_immutable(self):
        """Test that EntityID is immutable."""
        entity_id = EntityID.generate()
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            entity_id.value = EntityID.generate().value


class TestEntity:
    """Tests for Entity base class."""

    def test_entity_has_soft_delete_fields(self):
        """Test that Entity has deleted_at field."""
        entity = Entity(
            id=EntityID.generate(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None,
        )
        assert entity.deleted_at is None

    def test_entity_soft_delete_method(self):
        """Test that Entity has soft_delete() method."""
        entity = Entity(
            id=EntityID.generate(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None,
        )

        # Soft delete the entity
        entity.soft_delete()

        assert entity.deleted_at is not None
        assert isinstance(entity.deleted_at, datetime)

    def test_entity_is_deleted_property(self):
        """Test that Entity has is_deleted property."""
        entity = Entity(
            id=EntityID.generate(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
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
            id=EntityID.generate(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
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
            id=EntityID.generate(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None,
        )

        # Soft delete then restore
        entity.soft_delete()
        assert entity.is_deleted is True

        entity.restore()
        assert entity.is_deleted is False
        assert entity.deleted_at is None
