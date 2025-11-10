"""Common domain models and value objects."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    """Base class for all domain entities with ID and timestamps."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(frozen=True, default_factory=uuid4)
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
