"""Board API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    validate_body_account_id,
)
from leadr.boards.api.board_schemas import (
    BoardCreateRequest,
    BoardResponse,
    BoardUpdateRequest,
)
from leadr.boards.services.dependencies import BoardServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID
from leadr.common.domain.pagination import PaginationDirection

router = APIRouter()


@router.post("/boards", status_code=status.HTTP_201_CREATED, response_model=BoardResponse)
async def create_board(
    request: BoardCreateRequest, service: BoardServiceDep, auth: AuthContextDep
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
    validate_body_account_id(auth, request.account_id)

    try:
        board = await service.create_board(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            icon=request.icon,
            short_code=request.short_code,
            unit=request.unit,
            is_active=request.is_active,
            sort_direction=request.sort_direction,
            keep_strategy=request.keep_strategy,
            template_id=request.template_id,
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
    board_id: BoardID, service: BoardServiceDep, auth: AuthContextDep
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


@router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards(
    service: BoardServiceDep,
    auth: AuthContextDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: AccountID | None = None,
    code: str | None = None,
) -> PaginatedResponse[BoardResponse]:
    """List boards filtered by account_id and/or short code with pagination.

    For regular users:
    - If account_id not provided, defaults to their API key's account
    - If account_id provided, must match their API key's account (403 otherwise)

    For superadmins:
    - Can provide any account_id or search by code only
    - At least one of account_id or code is required

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/boards?account_id=acc_123&limit=50&sort=name:asc

    Args:
        service: Injected board service dependency.
        auth: Authentication context with user info.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID to filter boards by.
        code: Optional short code to filter boards by.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
        422: Neither account_id nor code parameter provided (superadmins only).
    """
    # Handle account_id resolution based on user role
    if not auth.is_superadmin:
        # Regular users: auto-derive account_id if not provided
        user_account_id = auth.api_key.account_id
        if account_id is None:
            account_id = user_account_id
        elif account_id != user_account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to the specified account",
            )
    else:
        # Superadmins: require at least one parameter
        if account_id is None and code is None:
            raise HTTPException(
                status_code=422,
                detail="At least one of account_id or code parameter is required",
            )

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
    # If filtering by code only, check authorization on results
    if account_id is None and code is not None:
        filtered_boards = [
            board for board in result.items if auth.has_access_to_account(board.account_id)
        ]
        response_items = [BoardResponse.from_domain(board) for board in filtered_boards]
    else:
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


@router.patch("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: BoardID, request: BoardUpdateRequest, service: BoardServiceDep, auth: AuthContextDep
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
        template_id=request.template_id,
        template_name=request.template_name,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
        tags=request.tags,
    )

    return BoardResponse.from_domain(board)
