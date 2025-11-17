"""API pagination models and dependencies."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from leadr.common.domain.cursor import Cursor
from leadr.common.domain.pagination import SortDirection, SortField

T = TypeVar("T")


class PaginationParams:
    """
    FastAPI dependency for parsing pagination query parameters.

    Parses cursor, limit, and sort parameters from the query string.
    Always appends 'id:asc' to sort specification for stable sorting.
    """

    def __init__(
        self,
        cursor: str | None = Query(None, description="Pagination cursor for navigating results"),
        limit: int = Query(20, ge=1, le=100, description="Number of items per page (1-100)"),
        sort: str | None = Query(
            None,
            description="Sort specification (e.g., 'value:desc,created_at:asc')",
        ),
    ) -> None:
        """
        Initialize pagination parameters.

        Args:
            cursor: Optional base64-encoded cursor string
            limit: Page size (1-100, default 20)
            sort: Comma-separated sort spec (e.g., "score:desc,created_at:asc")
        """
        self.cursor_str = cursor
        self.limit = limit
        self.sort_spec = self._parse_sort(sort)
        self._decoded_cursor: Cursor | None = None

    def _parse_sort(self, sort: str | None) -> list[SortField]:
        """
        Parse sort specification into list of SortField objects.

        Always appends 'id:asc' for stable sorting if not already present.

        Args:
            sort: Comma-separated sort spec (e.g., "value:desc,created_at:asc")

        Returns:
            List of SortField objects

        Raises:
            ValueError: If sort specification is invalid
        """
        # Default sort if none specified
        if sort is None:
            return [
                SortField(name="created_at", direction=SortDirection.DESC),
                SortField(name="id", direction=SortDirection.ASC),
            ]

        fields = []
        for field_spec in sort.split(","):
            field_spec = field_spec.strip()
            if ":" not in field_spec:
                raise ValueError(
                    f"Invalid sort specification: {field_spec}. "
                    f"Expected 'field:asc' or 'field:desc'"
                )

            field_name, direction_str = field_spec.split(":", 1)
            field_name = field_name.strip()
            direction_str = direction_str.strip().lower()

            if direction_str not in ("asc", "desc"):
                raise ValueError(
                    f"Invalid sort direction: {direction_str}. Expected 'asc' or 'desc'"
                )

            direction = SortDirection.ASC if direction_str == "asc" else SortDirection.DESC
            fields.append(SortField(name=field_name, direction=direction))

        # Always append id:asc for stable sorting if not already present
        if not any(f.name == "id" for f in fields):
            fields.append(SortField(name="id", direction=SortDirection.ASC))

        return fields

    def decode_cursor(self) -> Cursor | None:
        """
        Decode the cursor if present.

        Returns:
            Decoded Cursor object or None if no cursor

        Raises:
            CursorValidationError: If cursor is invalid
        """
        if self._decoded_cursor is None and self.cursor_str is not None:
            self._decoded_cursor = Cursor.decode(self.cursor_str)
        return self._decoded_cursor

    def has_cursor(self) -> bool:
        """Check if a cursor is present."""
        return self.cursor_str is not None


class PaginationMeta(BaseModel):
    """Pagination metadata in API responses."""

    next_cursor: str | None = Field(
        None,
        description="Cursor for the next page of results",
    )
    prev_cursor: str | None = Field(
        None,
        description="Cursor for the previous page of results",
    )
    has_next: bool = Field(
        description="Whether there are more results after this page",
    )
    has_prev: bool = Field(
        description="Whether there are results before this page",
    )
    count: int = Field(
        description="Number of items in this page",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Wraps a list of items with pagination metadata.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [{"id": "scr_123", "value": 1000}],
                "pagination": {
                    "next_cursor": "eyJwdiI6WzEwMDAsMTIzXX0=",
                    "prev_cursor": None,
                    "has_next": True,
                    "has_prev": False,
                    "count": 20,
                },
            }
        }
    )

    data: list[T] = Field(
        description="List of items in this page",
    )
    pagination: PaginationMeta = Field(
        description="Pagination metadata",
    )
