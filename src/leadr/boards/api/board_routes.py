"""Board API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AdminAuthContextDep,
    AuthContext,
    ClientAuthContextDep,
)
from leadr.boards.api.board_schemas import (
    BoardCreateRequest,
    BoardResponse,
    BoardUpdateRequest,
)
from leadr.boards.services.dependencies import BoardServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID

router = APIRouter()
client_router = APIRouter()


@router.post("/boards", status_code=status.HTTP_201_CREATED, response_model=BoardResponse)
async def create_board(
    request: BoardCreateRequest, service: BoardServiceDep, auth: AdminAuthContextDep
) -> BoardResponse:
    """Create a new board.

    Creates a new leaderboard associated with an existing game and account.
    The game must belong to the specified account.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Board creation details including account_id, game_id, name, and settings.
        service: Injected board service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardResponse with the created board including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
    try:
        board = await service.create_board(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            slug=request.slug,
            icon=request.icon,
            short_code=request.short_code,
            unit=request.unit,
            is_active=request.is_active,
            sort_direction=request.sort_direction,
            keep_strategy=request.keep_strategy,
            created_from_template_id=request.created_from_template_id,
            template_name=request.template_name,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            tags=request.tags,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Game or account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return BoardResponse.from_domain(board)


@router.get("/boards/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: BoardID, service: BoardServiceDep, auth: AdminAuthContextDep
) -> BoardResponse:
    """Get a board by ID.

    Args:
        board_id: Unique identifier for the board.
        service: Injected board service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardResponse with full board details.

    Raises:
        403: User does not have access to this board's account.
        404: Board not found.
    """
    board = await service.get_by_id_or_raise(board_id)

    # Check authorization
    if not auth.has_access_to_account(board.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's account",
        )

    return BoardResponse.from_domain(board)


async def handle_list_boards(
    auth: AuthContext,
    service: BoardServiceDep,
    pagination: PaginationParams,
    account_id: AccountID,
    code: str | None,
) -> PaginatedResponse[BoardResponse]:
    """Shared handler for listing boards.

    Args:
        auth: Authentication context with user info.
        service: Injected board service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID to filter boards by.
        code: Optional short code to filter boards by.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
    """
    try:
        result = await service.list_boards(account_id=account_id, code=code, pagination=pagination)
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if account_id is not None:
        filters_dict["account_id"] = str(account_id)
    if code is not None:
        filters_dict["code"] = code

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=BoardResponse,
    )


@router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards_admin(
    auth: AdminAuthContextDep,
    service: BoardServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Filter by account ID")] = None,
    code: str | None = None,
) -> PaginatedResponse[BoardResponse]:
    """List boards (Admin API).

    For regular users:
    - If account_id not provided, defaults to their API key's account
    - If account_id provided and they are superadmin, can access any account
    - If account_id provided and NOT superadmin, must match their account (validated in AuthContext)

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/boards?account_id=acc_123&limit=50&sort=name:asc

    Args:
        auth: Admin authentication context with user info.
        service: Injected board service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID to filter boards by.
        code: Optional short code to filter boards by.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
    """
    return await handle_list_boards(auth, service, pagination, account_id or auth.account_id, code)


@client_router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards_client(
    auth: ClientAuthContextDep,
    service: BoardServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    code: str | None = None,
) -> PaginatedResponse[BoardResponse]:
    """List boards (Client API).

    Account ID is automatically derived from the authenticated device's account.
    Clients can optionally filter by short code to find specific boards.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/client/boards?code=WEEKLY-CHALLENGE&limit=50

    Args:
        auth: Client authentication context with device info.
        service: Injected board service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        code: Optional short code to filter boards by.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
    """
    # Account ID auto-derived from client auth, code search supported
    return await handle_list_boards(auth, service, pagination, auth.account_id, code)


@router.patch("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: BoardID,
    request: BoardUpdateRequest,
    service: BoardServiceDep,
    auth: AdminAuthContextDep,
) -> BoardResponse:
    """Update a board.

    Supports updating any board field or soft-deleting the board.

    Args:
        board_id: Unique identifier for the board.
        request: Board update details (all fields optional).
        service: Injected board service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardResponse with the updated board details.

    Raises:
        403: User does not have access to this board's account.
        404: Board not found.
    """
    # Fetch board to check authorization
    board = await service.get_by_id_or_raise(board_id)

    # Check authorization
    if not auth.has_access_to_account(board.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's account",
        )

    # Handle soft delete first
    if request.deleted is True:
        board = await service.soft_delete(board_id)
        return BoardResponse.from_domain(board)

    # Handle field updates using service method
    board = await service.update_board(
        board_id=board_id,
        name=request.name,
        icon=request.icon,
        short_code=request.short_code,
        unit=request.unit,
        is_active=request.is_active,
        sort_direction=request.sort_direction,
        keep_strategy=request.keep_strategy,
        created_from_template_id=request.created_from_template_id,
        template_name=request.template_name,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
        tags=request.tags,
    )

    return BoardResponse.from_domain(board)
