"""Common domain models and value objects."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    """Base class for all domain entities with ID and timestamps.

    Provides common functionality for domain entities including:
    - Auto-generated UUID primary key (or typed prefixed ID in subclasses)
    - Created/updated timestamps (UTC)
    - Soft delete support with deleted_at timestamp
    - Equality and hashing based on ID

    All domain entities should extend this base class. The ID and timestamps
    are automatically populated on entity creation and don't need to be
    provided by consumers.

    Subclasses can override the `id` field with a typed PrefixedID for better
    type safety and API clarity.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: Any = Field(
        frozen=True,
        default_factory=uuid4,
        description="Unique identifier (auto-generated UUID or typed ID)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when entity was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of last update (UTC)",
    )
    deleted_at: datetime | None = Field(
        default=None, description="Timestamp when entity was soft-deleted (UTC), or null if active"
    )

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted.

        Returns:
            True if the entity has a deleted_at timestamp, False otherwise.
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark entity as soft-deleted.

        Sets the deleted_at timestamp to the current UTC time. Entities that are
        already deleted are not affected (deleted_at remains at original deletion time).

        Example:
            >>> account = Account(name="Test", slug="test")
            >>> account.soft_delete()
            >>> assert account.is_deleted is True
        """
        if self.deleted_at is None:
            self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore a soft-deleted entity.

        Clears the deleted_at timestamp, making the entity active again.

        Example:
            >>> account.soft_delete()
            >>> account.restore()
            >>> assert account.is_deleted is False
        """
        self.deleted_at = None

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID.

        Two entities are considered equal if they have the same ID and are
        of the same class.

        Args:
            other: Object to compare with.

        Returns:
            True if both entities have the same ID and class.
        """
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Return hash based on ID.

        Allows entities to be used in sets and as dictionary keys.

        Returns:
            Hash of the entity's ID.
        """
        return hash(self.id)
