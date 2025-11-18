# Cursor-Based Pagination Pattern

This guide shows how to add cursor-based pagination to any domain in LEADR following the Score domain reference implementation.

## Overview

The pagination system provides:

- **Cursor-based navigation**: Efficient bidirectional pagination without offset/limit issues
- **Compound sorting**: Multiple sort fields with mixed ASC/DESC directions
- **State validation**: Cursors verify that sort/filter parameters haven't changed
- **Type safety**: Full type hints and Pydantic validation throughout

## Architecture

Pagination is implemented across all layers:

```
┌─────────────────────────────────────────────────────┐
│ HTTP Layer (FastAPI Routes)                        │
│ - Parse PaginationParams from query string         │
│ - Build cursors from PaginatedResult               │
│ - Return PaginatedResponse[T]                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Service Layer                                       │
│ - Pass pagination params to repository             │
│ - Return PaginatedResult from repository           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Repository Layer                                    │
│ - Validate sort fields                             │
│ - Decode and validate cursors                      │
│ - Build cursor WHERE clauses                       │
│ - Execute paginated query                          │
│ - Extract cursor positions from results            │
└─────────────────────────────────────────────────────┘
```

## Step-by-Step Implementation

### 1. Define Sortable Fields (Repository)

Add a set of valid sortable fields to your repository:

```python
# src/leadr/{domain}/services/repositories.py
class BoardRepository(BaseRepository[Board, BoardORM]):
    # Define which fields can be sorted
    SORTABLE_FIELDS = {
        "id",
        "name",
        "short_code",
        "created_at",
        "updated_at",
    }
```

**Guidelines:**

- Include fields that users will commonly sort by
- Avoid fields that are rarely used for sorting
- Always include `id`, `created_at`, and `updated_at`
- Avoid large text fields or JSON columns

### 2. Update Repository `filter()` Method

Add pagination support to your repository's filter method:

```python
async def filter(
    self,
    account_id: UUID4 | PrefixedID | None = None,
    # ... other filters
    pagination: PaginationParams | None = None,
    **kwargs: Any,
) -> list[Board] | PaginatedResult[Board]:
    """Filter boards with optional pagination."""
    # Existing filter logic
    if account_id is None:
        raise ValueError("account_id is required")

    query = select(BoardORM).where(
        BoardORM.account_id == self._extract_uuid(account_id),
        BoardORM.deleted_at.is_(None),
    )

    # Build filters dict for cursor validation
    filters_dict = {}
    if some_filter is not None:
        query = query.where(BoardORM.some_field == some_filter)
        filters_dict["some_filter"] = str(some_filter)

    # If no pagination, return list (backward compatibility)
    if pagination is None:
        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    # Validate sort fields
    for sort_field in pagination.sort_spec:
        if sort_field.name not in self.SORTABLE_FIELDS:
            raise ValueError(
                f"Unknown sort field: {sort_field.name}. "
                f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
            )

    # Handle cursor if present
    cursor = None
    if pagination.has_cursor():
        cursor = pagination.decode_cursor()
        cursor.validate_state(pagination.sort_spec, filters_dict)

    # Execute paginated query using BaseRepository helper
    return await self._execute_paginated_query(
        query=query,
        sort_fields=pagination.sort_spec,
        cursor=cursor,
        limit=pagination.limit,
    )
```

**Key Points:**

- Keep backward compatibility by returning `list` when no pagination
- Build `filters_dict` with string representations of active filters
- Validate sort fields before executing query
- Use `_execute_paginated_query()` helper from `BaseRepository`

### 3. Update Service Method

Update your service to accept and pass pagination parameters:

```python
# src/leadr/{domain}/services/{entity}_service.py
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.pagination_result import PaginatedResult

class BoardService(BaseService[Board, BoardRepository]):
    async def list_boards(
        self,
        account_id: AccountID,
        # ... other filters
        pagination: PaginationParams | None = None,
    ) -> list[Board] | PaginatedResult[Board]:
        """List boards with optional pagination."""
        return await self.repository.filter(
            account_id=account_id,
            # ... other filters
            pagination=pagination,
        )
```

### 4. Update API Route

Update the route to accept pagination and return paginated response:

```python
# src/leadr/{domain}/api/routes.py
from fastapi import Depends
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.pagination import PaginationDirection

@router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards(
    account_id: QueryAccountIDDep,
    service: BoardServiceDep,
    pagination: PaginationParams = Depends(),
    # ... other query params
) -> PaginatedResponse[BoardResponse]:
    """
    List boards with pagination.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/boards?account_id=acc_123&limit=50&sort=name:asc
    """
    try:
        result = await service.list_boards(
            account_id=account_id,
            # ... other filters
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors (same as repository)
    filters_dict = {}
    if some_filter is not None:
        filters_dict["some_filter"] = str(some_filter)

    # Build cursors from result positions
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    # Convert domain entities to response models
    response_items = [BoardResponse.from_domain(board) for board in result.items]

    # Build paginated response
    return PaginatedResponse(
        data=response_items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )
```

**Key Points:**

- Always use `pagination: PaginationParams = Depends()` for dependency injection
- Catch `CursorValidationError` and `ValueError` to return 400 errors
- Build `filters_dict` with the same logic as repository
- Convert `PaginatedResult` to `PaginatedResponse` with cursors

## Testing Pattern

Create comprehensive tests for pagination:

```python
# tests/leadr/{domain}/api/test_{entity}_pagination.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestBoardPagination:
    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: dict[str, str]
    ) -> None:
        """Test default pagination parameters."""
        response = await authenticated_client.get(
            f"/v1/boards?account_id={test_account['id']}"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_forward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: dict[str, str]
    ) -> None:
        """Test forward pagination with cursors."""
        # Create test data
        for i in range(25):
            # Create entities...
            pass

        # Get first page
        response = await authenticated_client.get(
            f"/v1/boards?account_id={test_account['id']}&limit=10"
        )
        page1 = response.json()

        # Navigate to second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/v1/boards?account_id={test_account['id']}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()

        # Verify no overlap
        page1_ids = {item["id"] for item in page1["data"]}
        page2_ids = {item["id"] for item in page2["data"]}
        assert len(page1_ids & page2_ids) == 0
```

## Common Patterns

### Custom Default Sort

Override the default sort in `PaginationParams`:

```python
# In your route
pagination = PaginationParams(
    cursor=request.query_params.get("cursor"),
    limit=int(request.query_params.get("limit", 20)),
    sort=request.query_params.get("sort", "name:asc"),  # Custom default
)
```

### Multiple Filters

Build filters dictionary consistently:

```python
filters_dict = {}
if board_id is not None:
    filters_dict["board_id"] = str(board_id)
if game_id is not None:
    filters_dict["game_id"] = str(game_id)
if status is not None:
    filters_dict["status"] = status.value
```

### Enum Filters

Handle enums in filter dictionary:

```python
if status is not None:
    query = query.where(BoardORM.status == status.value)
    filters_dict["status"] = status.value  # Store enum value, not enum
```

## Performance Considerations

### Database Indexes

Create compound indexes for common sort patterns:

```sql
-- For sorting by name + id
CREATE INDEX idx_boards_name_id ON boards(name, id);

-- For sorting by created_at + id
CREATE INDEX idx_boards_created_at_id ON boards(created_at DESC, id);
```

### Query Optimization

- Always include `id` in sort for index efficiency
- Limit sortable fields to indexed columns
- Use `EXPLAIN ANALYZE` to verify index usage

### Cursor Size

Cursors are base64-encoded JSON. Keep them small:

- Use short filter keys (e.g., "b_id" not "board_identifier")
- Avoid storing large values in filters
- Typical cursor size: 100-200 bytes

## Error Messages

Use consistent error messages:

```python
# Invalid sort field
raise ValueError(
    f"Unknown sort field: {field_name}. "
    f"Valid fields: {', '.join(sorted(SORTABLE_FIELDS))}"
)

# Cursor state mismatch
raise CursorValidationError(
    "Query parameters don't match cursor state. Start a new pagination sequence."
)

# Invalid cursor format
raise CursorValidationError(f"Invalid pagination cursor: {error}")
```

## API Documentation

Document pagination in route docstrings:

```python
"""
List boards for an account with pagination.

Pagination:
- Default: 20 items per page, sorted by created_at:desc,id:asc
- Custom sort: Use ?sort=field1:dir1,field2:dir2
- Valid sort fields: id, name, short_code, created_at, updated_at
- Navigation: Use next_cursor/prev_cursor from response

Query Parameters:
- account_id (required): Account ID to filter by
- cursor (optional): Pagination cursor from previous response
- limit (optional): Items per page (1-100, default 20)
- sort (optional): Sort specification (e.g., "name:asc,created_at:desc")

Example:
    GET /v1/boards?account_id=acc_123&limit=50&sort=name:asc
"""
```

## Checklist for Adding Pagination

- [ ] Add `SORTABLE_FIELDS` set to repository
- [ ] Update repository `filter()` signature to accept `pagination: PaginationParams | None`
- [ ] Validate sort fields in repository
- [ ] Build filters dictionary in repository
- [ ] Use `_execute_paginated_query()` from BaseRepository
- [ ] Update service signature to accept `pagination: PaginationParams | None`
- [ ] Pass pagination to repository in service
- [ ] Update route to inject `pagination: PaginationParams = Depends()`
- [ ] Add try/except for `CursorValidationError` and `ValueError`
- [ ] Build cursors from `PaginatedResult`
- [ ] Return `PaginatedResponse[EntityResponse]`
- [ ] Update route docstring with pagination info
- [ ] Write comprehensive pagination tests

## Reference Implementation

See the Score domain for a complete reference implementation:

- Repository: `src/leadr/scores/services/repositories.py`
- Service: `src/leadr/scores/services/score_service.py`
- Routes: `src/leadr/scores/api/score_routes.py`
- Tests: `tests/leadr/scores/api/test_score_pagination.py`
