"""API response models for board states."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.boards.domain.board_state import BoardState
from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID


class BoardStateResponse(BaseModel):
    """Response model for a board state (admin only).

    Board states represent the materialized ranking state for an identity on a board.
    They are computed from score events and used for leaderboard queries.
    """

    id: BoardStateID = Field(description="Unique identifier for the board state")
    board_id: BoardID = Field(description="ID of the board this state belongs to")
    identity_id: IdentityID = Field(description="ID of the identity this state is for")
    primary_value: float | None = Field(
        default=None, description="Rankable value (null if not rankable)"
    )
    aux: dict[str, Any] | None = Field(
        default=None, description="Board-type-specific auxiliary data"
    )
    created_at: datetime = Field(description="Timestamp when the state was created (UTC)")
    updated_at: datetime = Field(description="Timestamp when the state was last updated (UTC)")

    @classmethod
    def from_domain(cls, state: BoardState) -> "BoardStateResponse":
        """Convert domain entity to response model.

        Args:
            state: The domain BoardState entity to convert.

        Returns:
            BoardStateResponse with all fields populated from the domain entity.
        """
        return cls(
            id=state.id,
            board_id=state.board_id,
            identity_id=state.identity_id,
            primary_value=state.primary_value,
            aux=state.aux,
            created_at=state.created_at,
            updated_at=state.updated_at,
        )
