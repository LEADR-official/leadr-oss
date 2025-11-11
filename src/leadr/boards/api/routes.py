"""Board API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

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
async def create_board(request: BoardCreateRequest, service: BoardServiceDep) -> BoardResponse:
    """Create a new board.

    Creates a new leaderboard associated with an existing game and account.
    The game must belong to the specified account.

    Args:
        request: Board creation details including account_id, game_id, name, and settings.
        service: Injected board service dependency.

    Returns:
        BoardResponse with the created board including auto-generated ID and timestamps.

    Raises:
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
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
async def get_board(board_id: UUID, service: BoardServiceDep) -> BoardResponse:
    """Get a board by ID.

    Args:
        board_id: Unique identifier for the board.
        service: Injected board service dependency.

    Returns:
        BoardResponse with full board details.

    Raises:
        404: Board not found.
    """
    board = await service.get_by_id_or_raise(board_id)
    return BoardResponse.from_domain(board)


@router.get("/boards/by-code/{short_code}", response_model=BoardResponse)
async def get_board_by_short_code(short_code: str, service: BoardServiceDep) -> BoardResponse:
    """Get a board by its short code.

    Args:
        short_code: Globally unique short code for the board.
        service: Injected board service dependency.

    Returns:
        BoardResponse with full board details.

    Raises:
        404: Board not found.
    """
    board = await service.get_board_by_short_code(short_code)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return BoardResponse.from_domain(board)


@router.get("/boards", response_model=list[BoardResponse])
async def list_boards(
    account_id: UUID,
    service: BoardServiceDep,
) -> list[BoardResponse]:
    """List all boards for an account.

    Args:
        account_id: Account ID to filter boards by.
        service: Injected board service dependency.

    Returns:
        List of all active boards for the specified account.
    """
    boards = await service.list_boards_by_account(account_id)
    return [BoardResponse.from_domain(board) for board in boards]


@router.patch("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: UUID, request: BoardUpdateRequest, service: BoardServiceDep
) -> BoardResponse:
    """Update a board.

    Supports updating any board field or soft-deleting the board.

    Args:
        board_id: Unique identifier for the board.
        request: Board update details (all fields optional).
        service: Injected board service dependency.

    Returns:
        BoardResponse with the updated board details.

    Raises:
        404: Board not found.
    """
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
    request: BoardTemplateCreateRequest, service: BoardTemplateServiceDep
) -> BoardTemplateResponse:
    """Create a new board template.

    Creates a template for automatically generating boards at regular intervals.
    The game must belong to the specified account.

    Args:
        request: Template creation details including repeat_interval and configuration.
        service: Injected board template service dependency.

    Returns:
        BoardTemplateResponse with the created template including auto-generated ID.

    Raises:
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
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
    template_id: UUID, service: BoardTemplateServiceDep
) -> BoardTemplateResponse:
    """Get a board template by ID.

    Args:
        template_id: Unique identifier for the template.
        service: Injected board template service dependency.

    Returns:
        BoardTemplateResponse with full template details.

    Raises:
        404: Template not found.
    """
    template = await service.get_by_id_or_raise(template_id)
    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates", response_model=list[BoardTemplateResponse])
async def list_board_templates(
    account_id: UUID,
    service: BoardTemplateServiceDep,
    game_id: UUID | None = None,
) -> list[BoardTemplateResponse]:
    """List board templates for an account, optionally filtered by game.

    Args:
        account_id: Account ID to filter templates by (required).
        game_id: Optional game ID to filter templates by.
        service: Injected board template service dependency.

    Returns:
        List of board templates matching the filter criteria.
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
) -> BoardTemplateResponse:
    """Update a board template.

    Supports updating any template field or soft-deleting the template.

    Args:
        template_id: Unique identifier for the template.
        request: Template update details (all fields optional).
        service: Injected board template service dependency.

    Returns:
        BoardTemplateResponse with the updated template details.

    Raises:
        404: Template not found.
    """
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
