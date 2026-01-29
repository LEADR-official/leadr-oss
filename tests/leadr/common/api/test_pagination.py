"""Tests for API pagination models and dependencies."""

import pytest
from pydantic import BaseModel, Field, ValidationError

from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor
from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)
from leadr.common.domain.pagination_result import PaginatedResult


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

    def test_user_provided_sort_is_false_when_sort_is_none(self) -> None:
        """Test that _user_provided_sort is False when sort param is None."""
        params = PaginationParams(cursor=None, limit=20, sort=None)
        assert params._user_provided_sort is False

    def test_user_provided_sort_is_true_when_sort_is_provided(self) -> None:
        """Test that _user_provided_sort is True when sort param is provided."""
        params = PaginationParams(cursor=None, limit=20, sort="value:desc")
        assert params._user_provided_sort is True

    def test_user_provided_sort_is_true_even_for_default_sort(self) -> None:
        """Test that _user_provided_sort is True even when user provides default sort order."""
        # User explicitly passes the same sort as default - should still be marked as user-provided
        params = PaginationParams(cursor=None, limit=20, sort="created_at:desc,id:asc")
        assert params._user_provided_sort is True


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
        pagination = PaginationMeta(
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False,
            count=0,
        )

        with pytest.raises(ValidationError):
            PaginatedResponse(data="not-a-list", pagination=pagination)  # type: ignore[arg-type]

    def test_from_paginated_result_with_next_and_prev_cursors(self) -> None:
        """Test creating response from result with both next and prev cursors."""

        # Create test domain entity
        class TestDomain(BaseModel):
            id: str
            value: int

        # Create test response model
        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        # Create paginated result
        items = [TestDomain(id="1", value=100), TestDomain(id="2", value=200)]
        result = PaginatedResult(
            items=items,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(values=(200,), entity_id="2"),
            prev_position=CursorPosition(values=(100,), entity_id="1"),
        )

        # Create pagination params
        pagination = PaginationParams(cursor=None, limit=20, sort="value:desc")

        # Create filters
        filters = {"game_id": "game_123", "status": "active"}

        # Create response using factory method
        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        # Verify response data
        assert len(response.data) == 2
        assert response.data[0].id == "1"
        assert response.data[0].value == 100
        assert response.data[1].id == "2"
        assert response.data[1].value == 200

        # Verify pagination metadata
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is True
        assert response.pagination.count == 2

        # Verify cursors are encoded strings
        assert response.pagination.next_cursor is not None
        assert isinstance(response.pagination.next_cursor, str)
        assert response.pagination.prev_cursor is not None
        assert isinstance(response.pagination.prev_cursor, str)

        # Decode and verify next cursor
        next_cursor = Cursor.decode(response.pagination.next_cursor)
        assert next_cursor.position == CursorPosition(values=(200,), entity_id="2")
        assert next_cursor.direction == PaginationDirection.FORWARD
        assert next_cursor.filters == filters

        # Decode and verify prev cursor
        prev_cursor = Cursor.decode(response.pagination.prev_cursor)
        assert prev_cursor.position == CursorPosition(values=(100,), entity_id="1")
        assert prev_cursor.direction == PaginationDirection.BACKWARD
        assert prev_cursor.filters == filters

    def test_from_paginated_result_with_only_next_cursor(self) -> None:
        """Test creating response from result with only next cursor."""

        class TestDomain(BaseModel):
            id: str
            value: int

        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        items = [TestDomain(id="1", value=100)]
        result = PaginatedResult(
            items=items,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=(100,), entity_id="1"),
            prev_position=None,
        )

        pagination = PaginationParams(cursor=None, limit=20, sort=None)
        filters: dict[str, str] = {}

        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        assert response.pagination.has_next is True
        assert response.pagination.has_prev is False
        assert response.pagination.next_cursor is not None
        assert response.pagination.prev_cursor is None

    def test_from_paginated_result_with_only_prev_cursor(self) -> None:
        """Test creating response from result with only prev cursor."""

        class TestDomain(BaseModel):
            id: str
            value: int

        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        items = [TestDomain(id="1", value=100)]
        result = PaginatedResult(
            items=items,
            has_next=False,
            has_prev=True,
            next_position=None,
            prev_position=CursorPosition(values=(100,), entity_id="1"),
        )

        pagination = PaginationParams(cursor=None, limit=20, sort=None)
        filters: dict[str, str] = {}

        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        assert response.pagination.has_next is False
        assert response.pagination.has_prev is True
        assert response.pagination.next_cursor is None
        assert response.pagination.prev_cursor is not None

    def test_from_paginated_result_with_no_cursors(self) -> None:
        """Test creating response from result with no cursors (single page)."""

        class TestDomain(BaseModel):
            id: str
            value: int

        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        items = [TestDomain(id="1", value=100)]
        result = PaginatedResult(
            items=items,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        pagination = PaginationParams(cursor=None, limit=20, sort=None)
        filters: dict[str, str] = {}

        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False
        assert response.pagination.next_cursor is None
        assert response.pagination.prev_cursor is None
        assert response.pagination.count == 1

    def test_from_paginated_result_with_empty_items(self) -> None:
        """Test creating response from result with no items."""

        class TestDomain(BaseModel):
            id: str
            value: int

        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        pagination = PaginationParams(cursor=None, limit=20, sort=None)
        filters: dict[str, str] = {}

        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        assert len(response.data) == 0
        assert response.pagination.count == 0
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False

    def test_from_paginated_result_filters_included_in_cursors(self) -> None:
        """Test that filters are correctly included in encoded cursors."""

        class TestDomain(BaseModel):
            id: str
            value: int

        class TestResponse(BaseModel):
            id: str = Field()
            value: int = Field()

            @classmethod
            def from_domain(cls, domain: TestDomain) -> "TestResponse":
                return cls(id=domain.id, value=domain.value)

        items = [TestDomain(id="1", value=100)]
        result = PaginatedResult(
            items=items,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=(100,), entity_id="1"),
            prev_position=None,
        )

        pagination = PaginationParams(cursor=None, limit=20, sort=None)
        filters = {
            "game_id": "game_123",
            "board_id": "board_456",
            "device_id": "device_789",
        }

        response = PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters,
            response_model=TestResponse,
        )

        # Decode cursor and verify filters
        assert response.pagination.next_cursor is not None
        next_cursor = Cursor.decode(response.pagination.next_cursor)
        assert next_cursor.filters == filters
