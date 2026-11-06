"""Score service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends, Request

from leadr.common.dependencies import DatabaseSession
from leadr.common.utils.sdk_info import parse_sdk_info, version_less_than
from leadr.config import settings
from leadr.scores.services.score_event_service import ScoreEventService
from leadr.scores.services.score_flag_service import ScoreFlagService
from leadr.scores.services.score_service import ScoreService
from leadr.scores.services.score_submission_meta_service import ScoreSubmissionMetaService


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


async def get_score_submission_meta_service(
    db: DatabaseSession,
) -> ScoreSubmissionMetaService:
    """Get ScoreSubmissionMetaService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        Initialized ScoreSubmissionMetaService instance
    """
    return ScoreSubmissionMetaService(db)


ScoreSubmissionMetaServiceDep = Annotated[
    ScoreSubmissionMetaService, Depends(get_score_submission_meta_service)
]


async def get_score_event_service(db: DatabaseSession) -> ScoreEventService:
    """Get ScoreEventService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        Initialized ScoreEventService instance
    """
    return ScoreEventService(db)


ScoreEventServiceDep = Annotated[ScoreEventService, Depends(get_score_event_service)]


def has_fingerprint_collision_bug(request: Request) -> bool:
    """Check if request is from SDK with fingerprint collision bug on web.

    Godot SDK <0.2.0 on web builds has OS.get_unique_id() returning empty,
    causing all web players to generate near-identical fingerprints.
    This means they share the same identity and hit rate limits collectively.

    Args:
        request: FastAPI request object

    Returns:
        True if request is from affected SDK version, False otherwise
    """
    user_agent = request.headers.get("user-agent", "")
    sdk_info = parse_sdk_info(user_agent)

    if sdk_info is None:
        return False

    # Only affects Godot SDK on web platform
    if sdk_info.sdk_type != "sdk-godot" or sdk_info.platform != "web":
        return False

    # Check if version is older than the fix version
    return version_less_than(sdk_info.version, settings.GODOT_SDK_FINGERPRINT_FIX_VERSION)


HasFingerprintCollisionBugDep = Annotated[bool, Depends(has_fingerprint_collision_bug)]
