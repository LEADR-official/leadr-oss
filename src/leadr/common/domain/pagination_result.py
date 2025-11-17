"""Pagination result from repository layer."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from leadr.common.domain.pagination import CursorPosition

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """
    Result of a paginated query from the repository layer.

    Attributes:
        items: List of entities returned by the query
        has_next: Whether there are more results after these items
        has_prev: Whether there are results before these items
        next_position: Position for the next page cursor (if has_next)
        prev_position: Position for the previous page cursor (if has_prev)
    """

    items: list[T]
    has_next: bool
    has_prev: bool
    next_position: CursorPosition | None
    prev_position: CursorPosition | None

    @property
    def count(self) -> int:
        """Return the number of items in this page."""
        return len(self.items)
