"""Cursor-based pagination implementation."""

import base64
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)

# Note: datetime and UUID imports are kept for _serialize_cursor_value() function


class CursorValidationError(ValueError):
    """Raised when cursor validation fails."""


def _serialize_cursor_value(value: Any) -> Any:
    """Convert cursor position values to JSON-serializable format.

    Args:
        value: Value from cursor position (could be datetime, UUID, primitives, etc.)

    Returns:
        JSON-serializable version of the value
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    # Handle Pydantic models and other objects with __str__
    if hasattr(value, "model_dump"):
        # Pydantic v2 model - serialize to string representation
        return str(value)
    if hasattr(value, "dict"):
        # Pydantic v1 model - serialize to string representation
        return str(value)
    return value


def _deserialize_cursor_value(value: Any) -> Any:
    """Convert JSON-deserialized value back to original type.

    Args:
        value: JSON-deserialized value (string, number, etc.)

    Returns:
        Value as-is (preserves JSON primitives: str, int, float, bool, None)

    Note:
        Cursor values are intentionally kept as JSON primitives after deserialization.
        SQLAlchemy handles type conversion when these values are used in queries.
        This ensures cursor encode/decode is truly a roundtrip for primitive values.
    """
    return value


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
        # Serialize position values (convert datetime to ISO format, etc.)
        serialized_values = [_serialize_cursor_value(v) for v in self.position.values]

        # Serialize filter values (convert complex objects to JSON-serializable types)
        serialized_filters = {k: _serialize_cursor_value(v) for k, v in self.filters.items()}

        data = {
            "pv": serialized_values,  # position values
            "pid": self.position.entity_id,  # position id
            "sf": [
                {"n": sf.name, "d": sf.direction.value} for sf in self.sort_fields
            ],  # sort fields
            "f": serialized_filters,  # filters (now serialized)
            "dir": self.direction.value,  # direction
        }
        try:
            json_str = json.dumps(data, separators=(",", ":"))
        except TypeError as e:
            # Debug: print what failed to serialize
            import sys

            print(f"ERROR encoding cursor: {e}", file=sys.stderr)
            print(f"  position.values: {self.position.values}", file=sys.stderr)
            print(f"  serialized_values: {serialized_values}", file=sys.stderr)
            print(f"  filters: {self.filters}", file=sys.stderr)
            print(f"  serialized_filters: {serialized_filters}", file=sys.stderr)
            raise
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
            decoded_bytes = base64.urlsafe_b64decode(cursor_str.encode())
            decoded = decoded_bytes.decode()
            data = json.loads(decoded)

            # Validate required fields
            required = ["pv", "pid", "sf", "f", "dir"]
            if not all(k in data for k in required):
                raise CursorValidationError("Cursor missing required fields")

            # Deserialize position values (convert ISO strings back to datetime, etc.)
            deserialized_values = [_deserialize_cursor_value(v) for v in data["pv"]]

            # Reconstruct objects
            position = CursorPosition(
                values=tuple(deserialized_values),
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
        except UnicodeDecodeError as e:
            # Debug: Show what we got
            import sys

            print(f"ERROR decoding cursor: {e}", file=sys.stderr)
            print(f"  cursor_str (first 100 chars): {cursor_str[:100]}", file=sys.stderr)
            try:
                decoded_bytes = base64.urlsafe_b64decode(cursor_str.encode())
                print(f"  decoded_bytes (first 100): {decoded_bytes[:100]}", file=sys.stderr)
                print(f"  decoded_bytes hex: {decoded_bytes[:50].hex()}", file=sys.stderr)
            except Exception:  # noqa: S110
                pass  # Best-effort debug output, ignore any errors
            raise CursorValidationError(f"Invalid pagination cursor: {e}") from e
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
