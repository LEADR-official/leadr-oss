"""API request and response models for scores."""

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreEventID, ScoreID
from leadr.config import settings
from leadr.scores.domain.anti_cheat.enums import ScoreStatus


def _parse_score_event_id(raw: str) -> ScoreEventID:
    """Parse ScoreEventID from aux data, handling both prefixed and raw UUID formats."""
    try:
        return ScoreEventID(raw)
    except ValueError:
        return ScoreEventID(UUID(raw))


class IsTestFilter(str, Enum):
    """Filter options for is_test query parameter in admin score listing."""

    TRUE = "true"
    FALSE = "false"
    ALL = "all"


class ScoreCreateRequestBase(BaseModel):
    """Base request model for score creation with common fields."""

    board_id: BoardID = Field(description="ID of the board this score belongs to")
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score for sorting/comparison")
    value_display: str | None = Field(
        default=None,
        description="Optional formatted display string (e.g., '1:23.45', '1,234 points')",
    )
    metadata: Any | None = Field(
        default=None,
        description="Optional JSON metadata for game-specific data (max 1KB)",
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, v: Any) -> Any:
        """Validate that metadata does not exceed size limit."""
        if v is None:
            return None

        # Serialize to compact JSON and check string length
        compacted = json.dumps(v, separators=(",", ":"))
        if len(compacted) > settings.SCORE_METADATA_MAX_SIZE_BYTES:
            raise ValueError(
                f"Metadata exceeds {settings.SCORE_METADATA_MAX_SIZE_BYTES} char limit "
                f"(got {len(compacted)} chars)"
            )

        return v


class ScoreClientCreateRequest(ScoreCreateRequestBase):
    """Request model for creating a score (Client API).

    For client authentication, account_id, game_id, and device_id are automatically
    derived from the authenticated device session. Only game-specific fields are required.

    Note: Timezone, country, and city are automatically populated from the client's
    IP address via GeoIP middleware.
    """

    # All fields inherited from ScoreCreateRequestBase


class ScoreResponse(BaseModel):
    """Response model for a score.

    This response model is built from BoardState or RunEntry data
    with denormalized fields for query efficiency.
    """

    id: ScoreID = Field(description="Unique identifier for the score")
    account_id: AccountID = Field(description="ID of the account this score belongs to")
    game_id: GameID = Field(description="ID of the game this score belongs to")
    board_id: BoardID = Field(description="ID of the board this score belongs to")
    identity_id: IdentityID = Field(description="ID of the identity that submitted this score")
    score_event_id: ScoreEventID | None = Field(
        default=None,
        description="ID of the score event that created/updated this score. "
        "Null for RATIO boards which derive values from other boards.",
    )
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score")
    value_display: str | None = Field(default=None, description="Formatted display string, or null")
    timezone: str | None = Field(default=None, description="Timezone for categorization, or null")
    country: str | None = Field(default=None, description="Country for categorization, or null")
    city: str | None = Field(default=None, description="City for categorization, or null")
    metadata: Any | None = Field(default=None, description="Game-specific metadata, or null")
    rank: int | None = Field(
        default=None,
        description="Leaderboard position (1 = first). Null if not querying by board_id.",
    )
    is_placeholder: bool = Field(
        default=False,
        description="True if this is a synthetic placeholder score (from around_score_value query)",
    )
    is_test: bool = Field(
        default=False,
        description="True if this score was submitted in test mode",
    )
    status: ScoreStatus = Field(
        description="Score lifecycle status (active, under_review, rejected)",
    )
    created_at: datetime = Field(description="Timestamp when the score was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_board_state(
        cls,
        state: BoardState,
        account_id: AccountID,
        game_id: GameID,
        rank: int,
    ) -> "ScoreResponse":
        """Convert BoardState to ScoreResponse with masked ID.

        Uses denormalized fields from BoardState directly, no joins required.

        Args:
            state: The BoardState entity representing materialized ranking.
            account_id: The account ID (from board lookup).
            game_id: The game ID (from board lookup).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreResponse with ID masked from bst_ to scr_ prefix.
        """
        # Mask BoardStateID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(state.id.uuid)

        # Extract score_event_id from aux field based on board type
        # RUN_IDENTITY stores selected_event_id, COUNTER stores last_event_id
        # RATIO boards don't have an event ID (they derive from other boards)
        score_event_id: ScoreEventID | None = None
        if state.aux:
            if "selected_event_id" in state.aux:
                score_event_id = _parse_score_event_id(state.aux["selected_event_id"])
            elif "last_event_id" in state.aux:
                score_event_id = _parse_score_event_id(state.aux["last_event_id"])

        return cls(
            id=masked_id,
            account_id=account_id,
            game_id=game_id,
            board_id=state.board_id,
            identity_id=state.identity_id,
            score_event_id=score_event_id,
            player_name=state.player_name,
            value=state.primary_value or 0.0,
            value_display=state.value_display,
            timezone=state.timezone,
            country=state.country,
            city=state.city,
            metadata=state.metadata,
            rank=rank,
            is_placeholder=state.is_placeholder,
            is_test=state.is_test,
            status=ScoreStatus.ACTIVE,  # Board states are always active
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    @classmethod
    def from_run_entry(
        cls,
        entry: RunEntry,
        account_id: AccountID,
        game_id: GameID,
        rank: int,
    ) -> "ScoreResponse":
        """Convert RunEntry to ScoreResponse with masked ID.

        Uses denormalized fields from RunEntry directly, no joins required.

        Args:
            entry: The RunEntry entity representing a single run.
            account_id: The account ID (from board lookup).
            game_id: The game ID (from board lookup).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreResponse with ID masked from run_ to scr_ prefix.
        """
        # Mask RunEntryID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(entry.id.uuid)

        return cls(
            id=masked_id,
            account_id=account_id,
            game_id=game_id,
            board_id=entry.board_id,
            identity_id=entry.identity_id,
            score_event_id=entry.score_event_id,
            player_name=entry.player_name,
            value=entry.primary_value,
            value_display=entry.value_display,
            timezone=entry.timezone,
            country=entry.country,
            city=entry.city,
            metadata=entry.metadata,
            rank=rank,
            is_placeholder=entry.is_placeholder,
            is_test=entry.is_test,
            status=ScoreStatus.ACTIVE,  # Run entries are always active
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class ScoreClientResponse(BaseModel):
    """Response model for a score returned to clients.

    Similar to ScoreResponse but excludes sensitive geo data (timezone, country, city)
    that clients should not see for other players' scores.
    """

    id: ScoreID = Field(description="Unique identifier for the score")
    account_id: AccountID = Field(description="ID of the account this score belongs to")
    game_id: GameID = Field(description="ID of the game this score belongs to")
    board_id: BoardID = Field(description="ID of the board this score belongs to")
    identity_id: IdentityID = Field(description="ID of the identity that submitted this score")
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score")
    value_display: str | None = Field(default=None, description="Formatted display string, or null")
    metadata: Any | None = Field(default=None, description="Game-specific metadata, or null")
    rank: int | None = Field(
        default=None,
        description="Leaderboard position (1 = first). Null if not querying by board_id.",
    )
    is_placeholder: bool = Field(
        default=False,
        description="True if this is a synthetic placeholder score (from around_score_value query)",
    )
    is_test: bool = Field(
        default=False,
        description="True if this score was submitted in test mode",
    )
    status: ScoreStatus = Field(
        description="Score lifecycle status (active, under_review, rejected)",
    )
    created_at: datetime = Field(description="Timestamp when the score was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_board_state(
        cls,
        state: BoardState,
        account_id: AccountID,
        game_id: GameID,
        rank: int,
    ) -> "ScoreClientResponse":
        """Convert BoardState to ScoreClientResponse with masked ID.

        Uses denormalized fields from BoardState directly, no joins required.

        Args:
            state: The BoardState entity representing materialized ranking.
            account_id: The account ID (from board lookup).
            game_id: The game ID (from board lookup).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreClientResponse with ID masked from bst_ to scr_ prefix.
        """
        # Mask BoardStateID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(state.id.uuid)

        return cls(
            id=masked_id,
            account_id=account_id,
            game_id=game_id,
            board_id=state.board_id,
            identity_id=state.identity_id,
            player_name=state.player_name,
            value=state.primary_value or 0.0,
            value_display=state.value_display,
            metadata=state.metadata,
            rank=rank,
            is_placeholder=state.is_placeholder,
            is_test=state.is_test,
            status=ScoreStatus.ACTIVE,  # Board states are always active
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    @classmethod
    def from_run_entry(
        cls,
        entry: RunEntry,
        account_id: AccountID,
        game_id: GameID,
        rank: int,
    ) -> "ScoreClientResponse":
        """Convert RunEntry to ScoreClientResponse with masked ID.

        Uses denormalized fields from RunEntry directly, no joins required.

        Args:
            entry: The RunEntry entity representing a single run.
            account_id: The account ID (from board lookup).
            game_id: The game ID (from board lookup).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreClientResponse with ID masked from run_ to scr_ prefix.
        """
        # Mask RunEntryID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(entry.id.uuid)

        return cls(
            id=masked_id,
            account_id=account_id,
            game_id=game_id,
            board_id=entry.board_id,
            identity_id=entry.identity_id,
            player_name=entry.player_name,
            value=entry.primary_value,
            value_display=entry.value_display,
            metadata=entry.metadata,
            rank=rank,
            is_placeholder=entry.is_placeholder,
            is_test=entry.is_test,
            status=ScoreStatus.ACTIVE,  # Run entries are always active
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
