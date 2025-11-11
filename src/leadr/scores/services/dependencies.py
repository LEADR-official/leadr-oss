"""Score service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.common.dependencies import DatabaseSession
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
