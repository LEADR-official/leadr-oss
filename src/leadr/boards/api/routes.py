"""Board API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.boards.api.schemas import (
    BoardCreateRequest,
    BoardResponse,
    BoardTemplateCreateRequest,
    BoardTemplateResponse,
    BoardTemplateUpdateRequest,
    BoardUpdateRequest,
)
from leadr.boards.services.dependencies import BoardServiceDep, BoardTemplateServiceDep

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
    board_id: UUID, service: BoardServiceDep, auth: AuthContextDep
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


@router.get("/boards", response_model=list[BoardResponse])
async def list_boards(
    service: BoardServiceDep,
    auth: AuthContextDep,
    account_id: UUID | None = None,
    code: str | None = None,
) -> list[BoardResponse]:
    """List boards filtered by account_id and/or short code.

    For regular users:
    - If account_id not provided, defaults to their API key's account
    - If account_id provided, must match their API key's account (403 otherwise)

    For superadmins:
    - Can provide any account_id or search by code only
    - At least one of account_id or code is required

    Args:
        service: Injected board service dependency.
        auth: Authentication context with user info.
        account_id: Optional account ID to filter boards by.
        code: Optional short code to filter boards by.

    Returns:
        List of boards matching the filter criteria.

    Raises:
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

    boards = await service.list_boards(account_id=account_id, code=code)

    # If filtering by code only, check authorization on results
    if account_id is None and code is not None:
        boards = [board for board in boards if auth.has_access_to_account(board.account_id)]

    return [BoardResponse.from_domain(board) for board in boards]


@router.patch("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: UUID, request: BoardUpdateRequest, service: BoardServiceDep, auth: AuthContextDep
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


# BoardTemplate routes


@router.post(
    "/board-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardTemplateResponse,
)
async def create_board_template(
    request: BoardTemplateCreateRequest, service: BoardTemplateServiceDep, auth: AuthContextDep
) -> BoardTemplateResponse:
    """Create a new board template.

    Creates a template for automatically generating boards at regular intervals.
    The game must belong to the specified account.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Template creation details including repeat_interval and configuration.
        service: Injected board template service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardTemplateResponse with the created template including auto-generated ID.

    Raises:
        403: User does not have access to the specified account.
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
    validate_body_account_id(auth, request.account_id)

    try:
        template = await service.create_board_template(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            repeat_interval=request.repeat_interval,
            next_run_at=request.next_run_at,
            is_active=request.is_active,
            name_template=request.name_template,
            config=request.config,
            config_template=request.config_template,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Game or account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def get_board_template(
    template_id: UUID, service: BoardTemplateServiceDep, auth: AuthContextDep
) -> BoardTemplateResponse:
    """Get a board template by ID.

    Args:
        template_id: Unique identifier for the template.
        service: Injected board template service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardTemplateResponse with full template details.

    Raises:
        403: User does not have access to this template's account.
        404: Template not found.
    """
    template = await service.get_by_id_or_raise(template_id)

    # Check authorization
    if not auth.has_access_to_account(template.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template's account",
        )

    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates", response_model=list[BoardTemplateResponse])
async def list_board_templates(
    account_id: QueryAccountIDDep,
    service: BoardTemplateServiceDep,
    game_id: UUID | None = None,
) -> list[BoardTemplateResponse]:
    """List board templates for an account, optionally filtered by game.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected board template service dependency.
        game_id: Optional game ID to filter templates by.

    Returns:
        List of board templates matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    if game_id is not None:
        templates = await service.list_board_templates_by_game(account_id, game_id)
    else:
        templates = await service.list_board_templates_by_account(account_id)

    return [BoardTemplateResponse.from_domain(template) for template in templates]


@router.patch("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def update_board_template(
    template_id: UUID,
    request: BoardTemplateUpdateRequest,
    service: BoardTemplateServiceDep,
    auth: AuthContextDep,
) -> BoardTemplateResponse:
    """Update a board template.

    Supports updating any template field or soft-deleting the template.

    Args:
        template_id: Unique identifier for the template.
        request: Template update details (all fields optional).
        service: Injected board template service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardTemplateResponse with the updated template details.

    Raises:
        403: User does not have access to this template's account.
        404: Template not found.
    """
    # Fetch template to check authorization
    template = await service.get_by_id_or_raise(template_id)

    # Check authorization
    if not auth.has_access_to_account(template.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template's account",
        )

    # Handle soft delete first
    if request.deleted is True:
        template = await service.soft_delete(template_id)
        return BoardTemplateResponse.from_domain(template)

    # Handle field updates
    template = await service.update_board_template(
        template_id=template_id,
        name=request.name,
        name_template=request.name_template,
        repeat_interval=request.repeat_interval,
        config=request.config,
        config_template=request.config_template,
        next_run_at=request.next_run_at,
        is_active=request.is_active,
    )

    return BoardTemplateResponse.from_domain(template)
