"""Common domain models and value objects."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


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


class Entity(BaseModel):
    """Base class for all domain entities with ID and timestamps."""

    model_config = ConfigDict(validate_assignment=True)

    id: EntityID = Field(frozen=True)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark entity as deleted."""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(timezone.utc)

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
