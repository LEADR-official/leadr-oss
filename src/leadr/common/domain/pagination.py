"""Pagination domain models."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PaginationDirection(str, Enum):
    """Direction of pagination."""

    FORWARD = "forward"
    BACKWARD = "backward"


class SortDirection(str, Enum):
    """Sort direction for fields."""

    ASC = "asc"
    DESC = "desc"

    def opposite(self) -> "SortDirection":
        """Return the opposite sort direction."""
        return SortDirection.DESC if self == SortDirection.ASC else SortDirection.ASC


@dataclass(frozen=True)
class SortField:
    """
    Specification for sorting a field.

    Attributes:
        name: Field name to sort by
        direction: ASC or DESC
    """

    name: str
    direction: SortDirection

    def __str__(self) -> str:
        """Return string representation like 'field:asc'."""
        return f"{self.name}:{self.direction.value}"


@dataclass(frozen=True)
class CursorPosition:
    """
    Position in a paginated result set.

    Attributes:
        values: List of values for each sort field at this position
        entity_id: The ID of the entity at this position (for stable sorting)
    """

    values: tuple[Any, ...]
    entity_id: str

    def __post_init__(self) -> None:
        """Validate that values is a tuple."""
        if not isinstance(self.values, tuple):
            # Convert to tuple if list was passed
            object.__setattr__(self, "values", tuple(self.values))
