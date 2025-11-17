"""Cursor-based pagination implementation."""

import base64
import json
from typing import Any

from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)


class CursorValidationError(ValueError):
    """Raised when cursor validation fails."""


class Cursor:
    """
    Opaque cursor for pagination that encodes position, sort, filters, and direction.

    The cursor ensures that pagination state (sort order, filters) remains consistent
    across page requests. If the client changes sort/filter parameters while using
    a cursor, validation will fail.
    """

    def __init__(
        self,
        position: CursorPosition,
        sort_fields: list[SortField],
        filters: dict[str, Any],
        direction: PaginationDirection,
    ) -> None:
        """
        Initialize a cursor.

        Args:
            position: The position in the result set (values + entity_id)
            sort_fields: List of sort fields that were applied
            filters: Dictionary of filter parameters that were applied
            direction: Direction of pagination (forward or backward)
        """
        self.position = position
        self.sort_fields = sort_fields
        self.filters = filters
        self.direction = direction

    def encode(self) -> str:
        """
        Encode cursor to base64 string.

        Returns:
            Base64-encoded JSON string representing the cursor state
        """
        data = {
            "pv": list(self.position.values),  # position values
            "pid": self.position.entity_id,  # position id
            "sf": [
                {"n": sf.name, "d": sf.direction.value} for sf in self.sort_fields
            ],  # sort fields
            "f": self.filters,  # filters
            "dir": self.direction.value,  # direction
        }
        json_str = json.dumps(data, separators=(",", ":"))
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        return encoded

    @classmethod
    def decode(cls, cursor_str: str) -> "Cursor":
        """
        Decode cursor from base64 string.

        Args:
            cursor_str: Base64-encoded cursor string

        Returns:
            Decoded Cursor object

        Raises:
            CursorValidationError: If cursor is invalid or malformed
        """
        try:
            decoded = base64.urlsafe_b64decode(cursor_str.encode()).decode()
            data = json.loads(decoded)

            # Validate required fields
            required = ["pv", "pid", "sf", "f", "dir"]
            if not all(k in data for k in required):
                raise CursorValidationError("Cursor missing required fields")

            # Reconstruct objects
            position = CursorPosition(
                values=tuple(data["pv"]),
                entity_id=data["pid"],
            )

            sort_fields = [
                SortField(name=sf["n"], direction=SortDirection(sf["d"])) for sf in data["sf"]
            ]

            direction = PaginationDirection(data["dir"])

            return cls(
                position=position,
                sort_fields=sort_fields,
                filters=data["f"],
                direction=direction,
            )
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise CursorValidationError(f"Invalid pagination cursor: {e}") from e

    def validate_state(self, sort_fields: list[SortField], filters: dict[str, Any]) -> None:
        """
        Validate that current query state matches cursor state.

        Args:
            sort_fields: Current sort fields
            filters: Current filter parameters

        Raises:
            CursorValidationError: If state doesn't match
        """
        # Compare sort fields
        if self.sort_fields != sort_fields:
            raise CursorValidationError(
                "Query parameters don't match cursor state. Start a new pagination sequence."
            )

        # Compare filters (ignore None values in current filters)
        current_filters = {k: v for k, v in filters.items() if v is not None}
        if self.filters != current_filters:
            raise CursorValidationError(
                "Query parameters don't match cursor state. Start a new pagination sequence."
            )

    def __eq__(self, other: object) -> bool:
        """Check equality with another cursor."""
        if not isinstance(other, Cursor):
            return False
        return (
            self.position == other.position
            and self.sort_fields == other.sort_fields
            and self.filters == other.filters
            and self.direction == other.direction
        )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"Cursor(position={self.position}, sort_fields={self.sort_fields}, "
            f"filters={self.filters}, direction={self.direction})"
        )
