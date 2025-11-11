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

    Validates that:
    - Board exists
    - Board belongs to the specified account
    - Game matches the board's game
    """
    try:
        score = await service.create_score(
            account_id=request.account_id,
            game_id=request.game_id,
            board_id=request.board_id,
            user_id=request.user_id,
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
            detail="Account, game, board, or user not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return ScoreResponse.from_domain(score)


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: UUID,
    service: ScoreServiceDep,
) -> ScoreResponse:
    """Get a score by ID."""
    score = await service.get_by_id_or_raise(score_id)
    return ScoreResponse.from_domain(score)


@router.get("/scores", response_model=list[ScoreResponse])
async def list_scores(
    account_id: UUID,
    board_id: UUID | None = None,
    game_id: UUID | None = None,
    user_id: UUID | None = None,
    service: ScoreServiceDep = None,  # type: ignore[assignment]
) -> list[ScoreResponse]:
    """List scores for an account with optional filters.

    Args:
        account_id: REQUIRED - Account ID to filter by
        board_id: Optional board ID to filter by
        game_id: Optional game ID to filter by
        user_id: Optional user ID to filter by
    """
    scores = await service.list_scores(
        account_id=account_id,
        board_id=board_id,
        game_id=game_id,
        user_id=user_id,
    )
    return [ScoreResponse.from_domain(score) for score in scores]


@router.patch("/scores/{score_id}", response_model=ScoreResponse)
async def update_score(
    score_id: UUID,
    request: ScoreUpdateRequest,
    service: ScoreServiceDep,
) -> ScoreResponse:
    """Update a score.

    Supports partial updates. Any field not provided will remain unchanged.
    Set `deleted: true` to soft delete the score.
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
