"""Score service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.common.dependencies import DatabaseSession
from leadr.scores.services.score_flag_service import ScoreFlagService
from leadr.scores.services.score_service import ScoreService


async def get_score_service(db: DatabaseSession) -> ScoreService:
    """Get ScoreService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        Initialized ScoreService instance
    """
    return ScoreService(db)


ScoreServiceDep = Annotated[ScoreService, Depends(get_score_service)]


async def get_score_flag_service(db: DatabaseSession) -> ScoreFlagService:
    """Get ScoreFlagService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        Initialized ScoreFlagService instance
    """
    return ScoreFlagService(db)


ScoreFlagServiceDep = Annotated[ScoreFlagService, Depends(get_score_flag_service)]
