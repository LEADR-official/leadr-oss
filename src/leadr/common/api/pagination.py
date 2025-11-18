"""API pagination models and dependencies."""

from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from leadr.common.domain.cursor import Cursor
from leadr.common.domain.pagination import PaginationDirection, SortDirection, SortField
from leadr.common.domain.pagination_result import PaginatedResult

T = TypeVar("T")
DomainT = TypeVar("DomainT")
ResponseT = TypeVar("ResponseT", bound=BaseModel)


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

    @classmethod
    def from_paginated_result(
        cls,
        result: PaginatedResult[DomainT],
        pagination: PaginationParams,
        filters: dict[str, Any],
        response_model: type[ResponseT],
    ) -> "PaginatedResponse[ResponseT]":
        """
        Create a PaginatedResponse from a PaginatedResult.

        This factory method abstracts away cursor construction, converting a repository-layer
        PaginatedResult into an API-layer PaginatedResponse with encoded cursors.

        Args:
            result: The paginated result from the repository layer
            pagination: The pagination parameters from the request
            filters: Dict of active filters to include in cursors (e.g., {"game_id": "123"})
            response_model: The response model class with a from_domain() method

        Returns:
            A fully constructed PaginatedResponse with encoded cursors and converted items

        Example:
            >>> return PaginatedResponse.from_paginated_result(
            ...     result=result,
            ...     pagination=pagination,
            ...     filters={"game_id": str(game_id)} if game_id else {},
            ...     response_model=ScoreResponse,
            ... )
        """
        # Build cursors from result positions
        next_cursor_str = None
        prev_cursor_str = None

        if result.next_position is not None:
            next_cursor = Cursor(
                position=result.next_position,
                sort_fields=pagination.sort_spec,
                filters=filters,
                direction=PaginationDirection.FORWARD,
            )
            next_cursor_str = next_cursor.encode()

        if result.prev_position is not None:
            prev_cursor = Cursor(
                position=result.prev_position,
                sort_fields=pagination.sort_spec,
                filters=filters,
                direction=PaginationDirection.BACKWARD,
            )
            prev_cursor_str = prev_cursor.encode()

        # Convert domain entities to response models
        # Type checker doesn't know response_model has from_domain, so we use type: ignore
        response_items: list[ResponseT] = [
            response_model.from_domain(item)  # type: ignore[attr-defined]
            for item in result.items
        ]

        # Build paginated response
        # Construct directly to avoid variance issues with generic type parameter
        return PaginatedResponse[ResponseT](
            data=response_items,
            pagination=PaginationMeta(
                next_cursor=next_cursor_str,
                prev_cursor=prev_cursor_str,
                has_next=result.has_next,
                has_prev=result.has_prev,
                count=result.count,
            ),
        )
