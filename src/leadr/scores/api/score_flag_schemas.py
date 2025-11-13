"""API request and response models for score flags."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.common.domain.ids import ScoreFlagID, ScoreID, UserID
from leadr.scores.domain.anti_cheat.models import ScoreFlag


class ScoreFlagUpdateRequest(BaseModel):
    """Request model for updating a score flag (reviewing)."""

    status: str | None = Field(
        default=None,
        description="Updated status: PENDING, CONFIRMED_CHEAT, FALSE_POSITIVE, or DISMISSED",
    )
    reviewer_decision: str | None = Field(
        default=None,
        description="Admin's decision/notes about the flag",
    )
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the flag")


class ScoreFlagResponse(BaseModel):
    """Response model for a score flag."""

    id: ScoreFlagID = Field(description="Unique identifier for the score flag")
    score_id: ScoreID = Field(description="ID of the score that was flagged")
    flag_type: str = Field(description="Type of flag (e.g., VELOCITY, DUPLICATE, RATE_LIMIT)")
    confidence: str = Field(description="Confidence level of the flag (LOW, MEDIUM, HIGH)")
    metadata: dict[str, Any] = Field(description="Additional metadata about the flag")
    status: str = Field(
        description="Status: PENDING, CONFIRMED_CHEAT, FALSE_POSITIVE, or DISMISSED"
    )
    reviewed_at: datetime | None = Field(
        default=None, description="Timestamp when flag was reviewed, or null"
    )
    reviewer_id: UserID | None = Field(
        default=None, description="ID of the user who reviewed this flag, or null"
    )
    reviewer_decision: str | None = Field(
        default=None, description="Admin's decision/notes, or null"
    )
    created_at: datetime = Field(description="Timestamp when the flag was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, flag: ScoreFlag) -> "ScoreFlagResponse":
        """Convert domain entity to response model.

        Args:
            flag: The domain ScoreFlag entity to convert.

        Returns:
            ScoreFlagResponse with all fields populated from the domain entity.
        """
        return cls(
            id=flag.id,
            score_id=flag.score_id,
            flag_type=flag.flag_type.value,
            confidence=flag.confidence.value,
            metadata=flag.metadata,
            status=flag.status.value,
            reviewed_at=flag.reviewed_at,
            reviewer_id=flag.reviewer_id,
            reviewer_decision=flag.reviewer_decision,
            created_at=flag.created_at,
            updated_at=flag.updated_at,
        )
