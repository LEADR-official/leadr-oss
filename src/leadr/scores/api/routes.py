"""API routes for score management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.scores.api.schemas import ScoreCreateRequest, ScoreResponse, ScoreUpdateRequest
from leadr.scores.services.dependencies import ScoreServiceDep

router = APIRouter()


@router.post("/scores", status_code=status.HTTP_201_CREATED)
async def create_score(
    request: ScoreCreateRequest,
    service: ScoreServiceDep,
) -> ScoreResponse:
    """Create a new score.

    Creates a new score submission for a board. Performs three-level validation:
    board exists, board belongs to the specified account, and game matches
    the board's game.

    Args:
        request: Score creation details including account_id, game_id, board_id,
                device_id, player_name, value, and optional filters.
        service: Injected score service dependency.

    Returns:
        ScoreResponse with the created score including auto-generated ID and timestamps.

    Raises:
        404: Account, game, board, or device not found.
        400: Validation failed (board doesn't belong to account, or game doesn't
            match board's game).
    """
    try:
        score = await service.create_score(
            account_id=request.account_id,
            game_id=request.game_id,
            board_id=request.board_id,
            device_id=request.device_id,
            player_name=request.player_name,
            value=request.value,
            value_display=request.value_display,
            filter_timezone=request.filter_timezone,
            filter_country=request.filter_country,
            filter_city=request.filter_city,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=404,
            detail="Account, game, board, or device not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return ScoreResponse.from_domain(score)


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: UUID,
    service: ScoreServiceDep,
) -> ScoreResponse:
    """Get a score by ID.

    Args:
        score_id: UUID of the score to retrieve.
        service: Injected score service dependency.

    Returns:
        ScoreResponse with the score details.

    Raises:
        404: Score not found or soft-deleted.
    """
    score = await service.get_by_id_or_raise(score_id)
    return ScoreResponse.from_domain(score)


@router.get("/scores", response_model=list[ScoreResponse])
async def list_scores(
    account_id: UUID,
    board_id: UUID | None = None,
    game_id: UUID | None = None,
    device_id: UUID | None = None,
    service: ScoreServiceDep = None,  # type: ignore[assignment]
) -> list[ScoreResponse]:
    """List scores for an account with optional filters.

    Returns all non-deleted scores for the specified account, with optional
    filtering by board, game, or device. Enforces multi-tenant safety by
    requiring account_id.

    Args:
        account_id: REQUIRED - Account ID to filter by (multi-tenant safety).
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        device_id: Optional device ID to filter by.
        service: Injected score service dependency.

    Returns:
        List of ScoreResponse objects matching the filter criteria.
    """
    scores = await service.list_scores(
        account_id=account_id,
        board_id=board_id,
        game_id=game_id,
        device_id=device_id,
    )
    return [ScoreResponse.from_domain(score) for score in scores]


@router.patch("/scores/{score_id}", response_model=ScoreResponse)
async def update_score(
    score_id: UUID,
    request: ScoreUpdateRequest,
    service: ScoreServiceDep,
) -> ScoreResponse:
    """Update a score.

    Supports partial updates of score fields. Any field not provided will
    remain unchanged. Set deleted: true to soft delete the score.

    Args:
        score_id: UUID of the score to update.
        request: Score update details with optional fields to modify.
        service: Injected score service dependency.

    Returns:
        ScoreResponse with the updated score details.

    Raises:
        404: Score not found or already soft-deleted.
    """
    # Handle soft delete
    if request.deleted is True:
        score = await service.soft_delete(score_id)
        return ScoreResponse.from_domain(score)

    # Update other fields
    score = await service.update_score(
        score_id=score_id,
        player_name=request.player_name,
        value=request.value,
        value_display=request.value_display,
        filter_timezone=request.filter_timezone,
        filter_country=request.filter_country,
        filter_city=request.filter_city,
    )
    return ScoreResponse.from_domain(score)
