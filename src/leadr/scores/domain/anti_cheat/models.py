"""Anti-cheat domain models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from leadr.common.domain.models import Entity
from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType


class AntiCheatResult(BaseModel):
    """Result of anti-cheat analysis on a score submission.

    This is a value object that encapsulates the decision made by the anti-cheat
    system. It indicates whether to accept, flag, or reject a score submission,
    along with the reasoning and supporting metadata.
    """

    model_config = {"frozen": True}

    action: FlagAction = Field(description="Action to take (ACCEPT/FLAG/REJECT)")
    confidence: FlagConfidence | None = Field(
        default=None, description="Confidence level of detection (if flagged/rejected)"
    )
    flag_type: FlagType | None = Field(
        default=None, description="Type of flag detected (if flagged/rejected)"
    )
    reason: str | None = Field(
        default=None, description="Human-readable reason for the action"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional context and data supporting the decision"
    )


class ScoreSubmissionMeta(Entity):
    """Metadata tracking submission history for anti-cheat analysis.

    Tracks the number and timing of score submissions per device/board combination
    to enable detection of suspicious patterns like rapid-fire submissions or
    excessive submission rates.
    """

    score_id: UUID = Field(description="ID of the most recent score submission")
    device_id: UUID = Field(description="ID of the device submitting scores")
    board_id: UUID = Field(description="ID of the board being submitted to")
    submission_count: int = Field(
        default=1, description="Total number of submissions by this device to this board"
    )
    last_submission_at: datetime = Field(
        description="Timestamp of the most recent submission"
    )




class ScoreFlag(Entity):
    """Record of an anti-cheat flag raised for a score submission.

    Represents a suspicious pattern detected by the anti-cheat system.
    Flags can be reviewed by admins to confirm or dismiss the detection.
    """

    score_id: UUID = Field(description="ID of the flagged score")
    flag_type: FlagType = Field(description="Type of suspicious behavior detected")
    confidence: FlagConfidence = Field(description="Confidence level of detection")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Supporting data for the detection"
    )
    status: str = Field(
        default="PENDING", description="Review status (PENDING/CONFIRMED_CHEAT/FALSE_POSITIVE/DISMISSED)"
    )
    reviewed_at: datetime | None = Field(
        default=None, description="When the flag was reviewed by an admin"
    )
    reviewer_id: UUID | None = Field(
        default=None, description="ID of the admin who reviewed the flag"
    )
    reviewer_decision: str | None = Field(
        default=None, description="Admin's decision/notes on the flag"
    )
