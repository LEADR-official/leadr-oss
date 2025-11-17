"""API schemas for score submission metadata."""

from datetime import datetime

from pydantic import BaseModel

from leadr.common.domain.ids import BoardID, DeviceID, ScoreID, ScoreSubmissionMetaID
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta


class ScoreSubmissionMetaResponse(BaseModel):
    """Response model for score submission metadata."""

    id: ScoreSubmissionMetaID
    score_id: ScoreID
    device_id: DeviceID
    board_id: BoardID
    submission_count: int
    last_submission_at: datetime
    last_score_value: float | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, meta: ScoreSubmissionMeta) -> "ScoreSubmissionMetaResponse":
        """Convert domain entity to API response."""
        return cls(
            id=meta.id,
            score_id=meta.score_id,
            device_id=meta.device_id,
            board_id=meta.board_id,
            submission_count=meta.submission_count,
            last_submission_at=meta.last_submission_at,
            last_score_value=meta.last_score_value,
            created_at=meta.created_at,
            updated_at=meta.updated_at,
        )
