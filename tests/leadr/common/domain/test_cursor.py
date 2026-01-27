"""Tests for cursor-based pagination."""

import base64
import json

import pytest

from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)


class TestCursor:
    """Test cursor encoding, decoding, and validation."""

    def test_encode_decode_roundtrip(self) -> None:
        """Test that encoding and decoding a cursor returns the same data."""
        position = CursorPosition(values=(100, "2025-01-15"), entity_id="test-id-123")
        sort_fields = [
            SortField(name="value", direction=SortDirection.DESC),
            SortField(name="created_at", direction=SortDirection.ASC),
        ]
        filters = {"board_id": "brd_123", "game_id": "gam_456"}
        direction = PaginationDirection.FORWARD

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=direction,
        )

        # Encode and decode
        encoded = cursor.encode()
        decoded = Cursor.decode(encoded)

        # Verify all fields match
        assert decoded.position == position
        assert decoded.sort_fields == sort_fields
        assert decoded.filters == filters
        assert decoded.direction == direction

    def test_encode_produces_base64_string(self) -> None:
        """Test that encode produces a valid base64 string."""
        position = CursorPosition(values=(50,), entity_id="abc")
        sort_fields = [SortField(name="id", direction=SortDirection.ASC)]
        filters = {}
        direction = PaginationDirection.FORWARD

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=direction,
        )

        encoded = cursor.encode()

        # Should be a string
        assert isinstance(encoded, str)
        # Should not contain spaces (base64)
        assert " " not in encoded
        # Should be decodable
        decoded = Cursor.decode(encoded)
        assert decoded.position == position

    def test_decode_invalid_base64_raises_error(self) -> None:
        """Test that decoding invalid base64 raises CursorValidationError."""
        with pytest.raises(CursorValidationError, match="Invalid pagination cursor"):
            Cursor.decode("not-valid-base64!!!")

    def test_decode_missing_fields_raises_error(self) -> None:
        """Test that decoding cursor with missing fields raises error."""
        # Create cursor with missing required field
        incomplete_data = {"pv": [100], "pid": "id"}  # Missing "sf", "f", "dir"
        encoded = base64.urlsafe_b64encode(json.dumps(incomplete_data).encode()).decode()

        with pytest.raises(CursorValidationError, match="Cursor missing required fields"):
            Cursor.decode(encoded)

    def test_validate_state_matching_succeeds(self) -> None:
        """Test that validating matching state succeeds without error."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [
            SortField(name="value", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]
        filters = {"board_id": "brd_123"}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        # Should not raise
        cursor.validate_state(sort_fields, filters)

    def test_validate_state_different_sort_raises_error(self) -> None:
        """Test that validating with different sort fields raises error."""
        position = CursorPosition(values=(100,), entity_id="id")
        original_sort = [SortField(name="value", direction=SortDirection.DESC)]
        filters = {}

        cursor = Cursor(
            position=position,
            sort_fields=original_sort,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        # Try to validate with different sort
        different_sort = [SortField(name="created_at", direction=SortDirection.ASC)]

        with pytest.raises(
            CursorValidationError, match="Query parameters don't match cursor state"
        ):
            cursor.validate_state(different_sort, filters)

    def test_validate_state_different_filters_raises_error(self) -> None:
        """Test that validating with different filters raises error."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="id", direction=SortDirection.ASC)]
        original_filters = {"board_id": "brd_123"}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=original_filters,
            direction=PaginationDirection.FORWARD,
        )

        # Try to validate with different filters
        different_filters = {"board_id": "brd_456"}

        with pytest.raises(
            CursorValidationError, match="Query parameters don't match cursor state"
        ):
            cursor.validate_state(sort_fields, different_filters)

    def test_validate_state_ignores_none_values_in_current_filters(self) -> None:
        """Test that validation ignores None values in current filters."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="id", direction=SortDirection.ASC)]
        original_filters = {"board_id": "brd_123"}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=original_filters,
            direction=PaginationDirection.FORWARD,
        )

        # Current filters have None values (should be ignored)
        current_filters = {"board_id": "brd_123", "game_id": None}

        # Should not raise - None values are filtered out
        cursor.validate_state(sort_fields, current_filters)

    def test_cursor_with_multiple_values(self) -> None:
        """Test cursor with multiple position values."""
        position = CursorPosition(
            values=(950, "2025-01-15T10:30:00Z", "extra-field"),
            entity_id="score-id-789",
        )
        sort_fields = [
            SortField(name="value", direction=SortDirection.DESC),
            SortField(name="created_at", direction=SortDirection.ASC),
            SortField(name="extra", direction=SortDirection.ASC),
            SortField(name="id", direction=SortDirection.ASC),
        ]
        filters = {}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.BACKWARD,
        )

        # Encode and decode
        encoded = cursor.encode()
        decoded = Cursor.decode(encoded)

        assert decoded.position.values == position.values
        assert decoded.position.entity_id == position.entity_id
        assert decoded.direction == PaginationDirection.BACKWARD

    def test_cursor_with_empty_filters(self) -> None:
        """Test cursor with no filters."""
        position = CursorPosition(values=(1,), entity_id="id")
        sort_fields = [SortField(name="id", direction=SortDirection.ASC)]
        filters = {}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        encoded = cursor.encode()
        decoded = Cursor.decode(encoded)

        assert decoded.filters == {}

    def test_cursor_equality(self) -> None:
        """Test cursor equality comparison."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="value", direction=SortDirection.DESC)]
        filters = {"board_id": "brd_123"}

        cursor1 = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )
        cursor2 = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        assert cursor1 == cursor2

    def test_cursor_inequality(self) -> None:
        """Test cursor inequality with different values."""
        position1 = CursorPosition(values=(100,), entity_id="id1")
        position2 = CursorPosition(values=(200,), entity_id="id2")
        sort_fields = [SortField(name="value", direction=SortDirection.DESC)]
        filters = {}

        cursor1 = Cursor(
            position=position1,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )
        cursor2 = Cursor(
            position=position2,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        assert cursor1 != cursor2

    def test_cursor_repr(self) -> None:
        """Test cursor repr for debugging."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="value", direction=SortDirection.DESC)]
        filters = {}

        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )

        repr_str = repr(cursor)
        assert "Cursor" in repr_str
        assert "position=" in repr_str
        assert "sort_fields=" in repr_str
