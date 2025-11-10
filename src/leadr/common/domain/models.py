"""Common domain models and value objects."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class EntityID(BaseModel):
    """Universal entity identifier."""

    model_config = ConfigDict(frozen=True)

    value: UUID

    @classmethod
    def generate(cls) -> "EntityID":
        """Generate a new unique ID."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "EntityID":
        """Create an ID from a string UUID."""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        """Return string representation of the ID."""
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Check equality based on UUID value."""
        if not isinstance(other, EntityID):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash of the UUID value."""
        return hash(self.value)


def _validate_entity_id(value: str | UUID | EntityID) -> EntityID:
    """Convert path parameter values to EntityID.

    Handles string UUIDs from path parameters, UUID objects, and EntityID objects.

    Args:
        value: String UUID, UUID object, or EntityID object

    Returns:
        EntityID instance

    Raises:
        ValueError: If the value cannot be converted to a valid UUID
    """
    if isinstance(value, EntityID):
        return value
    if isinstance(value, UUID):
        return EntityID(value=value)
    return EntityID.from_string(value)


# Type alias for route path parameters
UUIDParam = Annotated[EntityID, BeforeValidator(_validate_entity_id)]


class Entity(BaseModel):
    """Base class for all domain entities with ID and timestamps."""

    model_config = ConfigDict(validate_assignment=True)

    id: EntityID = Field(frozen=True, default_factory=EntityID.generate)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark entity as deleted."""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore a soft-deleted entity."""
        self.deleted_at = None

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Return hash based on ID."""
        return hash(self.id)
