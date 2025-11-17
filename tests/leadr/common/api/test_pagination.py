"""Tests for API pagination models and dependencies."""

import pytest

from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor
from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)


class TestPaginationParams:
    """Test PaginationParams dependency."""

    def test_default_parameters(self) -> None:
        """Test default pagination parameters."""
        params = PaginationParams(cursor=None, limit=20, sort=None)
        assert params.cursor_str is None
        assert params.limit == 20
        assert params.sort_spec == [
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

    def test_custom_limit(self) -> None:
        """Test custom limit parameter."""
        params = PaginationParams(cursor=None, limit=50, sort=None)
        assert params.limit == 50

    def test_parse_single_sort_field(self) -> None:
        """Test parsing single sort field."""
        params = PaginationParams(cursor=None, limit=20, sort="value:desc")
        assert len(params.sort_spec) == 2  # value:desc + id:asc (auto-added)
        assert params.sort_spec[0] == SortField(name="value", direction=SortDirection.DESC)
        assert params.sort_spec[1] == SortField(name="id", direction=SortDirection.ASC)

    def test_parse_multiple_sort_fields(self) -> None:
        """Test parsing multiple sort fields."""
        params = PaginationParams(cursor=None, limit=20, sort="value:desc,created_at:asc")
        assert len(params.sort_spec) == 3  # value:desc, created_at:asc, id:asc
        assert params.sort_spec[0] == SortField(name="value", direction=SortDirection.DESC)
        assert params.sort_spec[1] == SortField(name="created_at", direction=SortDirection.ASC)
        assert params.sort_spec[2] == SortField(name="id", direction=SortDirection.ASC)

    def test_parse_sort_with_id_already_present(self) -> None:
        """Test that id:asc is not duplicated if already in sort spec."""
        params = PaginationParams(cursor=None, limit=20, sort="value:desc,id:desc")
        # id:desc should not have id:asc added
        sort_names = [sf.name for sf in params.sort_spec]
        assert sort_names.count("id") == 1
        assert params.sort_spec[-1].name == "id"
        assert params.sort_spec[-1].direction == SortDirection.DESC

    def test_parse_invalid_sort_format_raises_error(self) -> None:
        """Test that invalid sort format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sort specification"):
            PaginationParams(cursor=None, limit=20, sort="value")  # Missing direction

    def test_parse_invalid_sort_direction_raises_error(self) -> None:
        """Test that invalid sort direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sort direction"):
            PaginationParams(cursor=None, limit=20, sort="value:up")  # Invalid direction

    def test_has_cursor_returns_true_when_cursor_present(self) -> None:
        """Test has_cursor returns True when cursor is provided."""
        params = PaginationParams(cursor="some-cursor-string", limit=20, sort=None)
        assert params.has_cursor() is True

    def test_has_cursor_returns_false_when_no_cursor(self) -> None:
        """Test has_cursor returns False when no cursor."""
        params = PaginationParams(cursor=None, limit=20, sort=None)
        assert params.has_cursor() is False

    def test_decode_cursor_returns_cursor_object(self) -> None:
        """Test decode_cursor returns Cursor object."""
        # Create a valid cursor
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="value", direction=SortDirection.DESC)]
        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        cursor_str = cursor.encode()

        # Decode via params
        params = PaginationParams(cursor=cursor_str, limit=20, sort=None)
        decoded = params.decode_cursor()

        assert decoded is not None
        assert decoded.position == position

    def test_decode_cursor_returns_none_when_no_cursor(self) -> None:
        """Test decode_cursor returns None when no cursor."""
        params = PaginationParams(cursor=None, limit=20, sort=None)
        assert params.decode_cursor() is None

    def test_decode_cursor_caches_result(self) -> None:
        """Test that decode_cursor caches the decoded cursor."""
        position = CursorPosition(values=(100,), entity_id="id")
        sort_fields = [SortField(name="value", direction=SortDirection.DESC)]
        cursor = Cursor(
            position=position,
            sort_fields=sort_fields,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        cursor_str = cursor.encode()

        params = PaginationParams(cursor=cursor_str, limit=20, sort=None)
        decoded1 = params.decode_cursor()
        decoded2 = params.decode_cursor()

        # Should be the same object (cached)
        assert decoded1 is decoded2


class TestPaginationMeta:
    """Test PaginationMeta model."""

    def test_create_pagination_meta(self) -> None:
        """Test creating pagination metadata."""
        meta = PaginationMeta(
            next_cursor="next-cursor",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=20,
        )
        assert meta.next_cursor == "next-cursor"
        assert meta.prev_cursor is None
        assert meta.has_next is True
        assert meta.has_prev is False
        assert meta.count == 20


class TestPaginatedResponse:
    """Test PaginatedResponse model."""

    def test_create_paginated_response(self) -> None:
        """Test creating paginated response."""
        data = [{"id": 1, "value": 100}, {"id": 2, "value": 200}]
        pagination = PaginationMeta(
            next_cursor="next",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            count=2,
        )

        response = PaginatedResponse(data=data, pagination=pagination)
        assert response.data == data
        assert response.pagination == pagination

    def test_validate_data_must_be_list(self) -> None:
        """Test that data must be a list."""
        from pydantic import ValidationError

        pagination = PaginationMeta(
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False,
            count=0,
        )

        with pytest.raises(ValidationError):
            PaginatedResponse(data="not-a-list", pagination=pagination)  # type: ignore[arg-type]
