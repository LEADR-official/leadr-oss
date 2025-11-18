"""Tests for pagination domain models."""

import pytest

from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)


class TestSortField:
    """Test SortField model."""

    def test_create_sort_field(self) -> None:
        """Test creating a sort field."""
        field = SortField(name="value", direction=SortDirection.DESC)
        assert field.name == "value"
        assert field.direction == SortDirection.DESC

    def test_sort_field_string_representation(self) -> None:
        """Test string representation of sort field."""
        field = SortField(name="created_at", direction=SortDirection.ASC)
        assert str(field) == "created_at:asc"

        field = SortField(name="value", direction=SortDirection.DESC)
        assert str(field) == "value:desc"

    def test_sort_field_equality(self) -> None:
        """Test sort field equality."""
        field1 = SortField(name="value", direction=SortDirection.DESC)
        field2 = SortField(name="value", direction=SortDirection.DESC)
        field3 = SortField(name="value", direction=SortDirection.ASC)

        assert field1 == field2
        assert field1 != field3

    def test_sort_field_immutable(self) -> None:
        """Test that sort field is immutable (frozen dataclass)."""
        field = SortField(name="value", direction=SortDirection.DESC)
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            field.name = "other"  # type: ignore[misc]


class TestCursorPosition:
    """Test CursorPosition model."""

    def test_create_cursor_position(self) -> None:
        """Test creating a cursor position."""
        position = CursorPosition(values=(100, "2025-01-15"), entity_id="test-id")
        assert position.values == (100, "2025-01-15")
        assert position.entity_id == "test-id"

    def test_cursor_position_converts_list_to_tuple(self) -> None:
        """Test that list values are converted to tuple."""
        position = CursorPosition(values=[100, 200], entity_id="id")  # type: ignore[arg-type]
        assert isinstance(position.values, tuple)
        assert position.values == (100, 200)

    def test_cursor_position_single_value(self) -> None:
        """Test cursor position with single value."""
        position = CursorPosition(values=(42,), entity_id="single")
        assert position.values == (42,)
        assert len(position.values) == 1

    def test_cursor_position_equality(self) -> None:
        """Test cursor position equality."""
        pos1 = CursorPosition(values=(100, "2025-01-15"), entity_id="id")
        pos2 = CursorPosition(values=(100, "2025-01-15"), entity_id="id")
        pos3 = CursorPosition(values=(200, "2025-01-15"), entity_id="id")

        assert pos1 == pos2
        assert pos1 != pos3

    def test_cursor_position_immutable(self) -> None:
        """Test that cursor position is immutable."""
        position = CursorPosition(values=(100,), entity_id="id")
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            position.entity_id = "other"  # type: ignore[misc]


class TestPaginationDirection:
    """Test PaginationDirection enum."""

    def test_forward_direction(self) -> None:
        """Test forward direction value."""
        assert PaginationDirection.FORWARD.value == "forward"

    def test_backward_direction(self) -> None:
        """Test backward direction value."""
        assert PaginationDirection.BACKWARD.value == "backward"

    def test_direction_from_string(self) -> None:
        """Test creating direction from string."""
        forward = PaginationDirection("forward")
        backward = PaginationDirection("backward")

        assert forward == PaginationDirection.FORWARD
        assert backward == PaginationDirection.BACKWARD


class TestSortDirection:
    """Test SortDirection enum."""

    def test_asc_direction(self) -> None:
        """Test ascending direction value."""
        assert SortDirection.ASC.value == "asc"

    def test_desc_direction(self) -> None:
        """Test descending direction value."""
        assert SortDirection.DESC.value == "desc"

    def test_direction_from_string(self) -> None:
        """Test creating direction from string."""
        asc = SortDirection("asc")
        desc = SortDirection("desc")

        assert asc == SortDirection.ASC
        assert desc == SortDirection.DESC
