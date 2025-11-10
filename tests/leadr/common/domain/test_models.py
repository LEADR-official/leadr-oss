"""Tests for common domain models."""

from datetime import UTC, datetime
from uuid import uuid4

from leadr.common.domain.models import Entity


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
