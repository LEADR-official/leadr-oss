"""API request and response models for scores."""

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from leadr.auth.domain.identity import Identity
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, IdentityID, ScoreID
from leadr.config import settings
from leadr.scores.domain.anti_cheat.enums import ScoreStatus
from leadr.scores.domain.score import Score
from leadr.scores.domain.score_event import ScoreEvent


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


class ScoreCreateRequest(ScoreCreateRequestBase):
    """Request model for creating a score (Admin API).

    Note: Timezone, country, and city are automatically populated from the client's
    IP address via GeoIP middleware but can be overriden by admins in the request body.

    For regular admins: account_id is derived from auth context, must provide game_id and
    device_id. For superadmins: can provide account_id to create scores for any account,
    must provide game_id and device_id.
    """

    account_id: AccountID | None = Field(
        default=None,
        description=(
            "ID of the account (only for superadmins, regular admins use their auth account)"
        ),
    )
    game_id: GameID = Field(
        description="ID of the game this score belongs to (required for admin API)",
    )
    device_id: DeviceID = Field(
        description="ID of the device that submitted this score (required for admin API)",
    )
    timezone: str | None = Field(
        default=None,
        description="Optional override of GeoIP metadata",
    )
    country: str | None = Field(
        default=None,
        description="Optional override of GeoIP metadata",
    )
    city: str | None = Field(
        default=None,
        description="Optional override of GeoIP metadata",
    )


class ScoreClientCreateRequest(ScoreCreateRequestBase):
    """Request model for creating a score (Client API).

    For client authentication, account_id, game_id, and device_id are automatically
    derived from the authenticated device session. Only game-specific fields are required.

    Note: Timezone, country, and city are automatically populated from the client's
    IP address via GeoIP middleware.
    """

    # All fields inherited from ScoreCreateRequestBase


class ScoreUpdateRequest(BaseModel):
    """Request model for updating a score."""

    player_name: str | None = Field(default=None, description="Updated player name")
    value: float | None = Field(default=None, description="Updated score value")
    value_display: str | None = Field(default=None, description="Updated display string")
    timezone: str | None = Field(default=None, description="Updated timezone")
    country: str | None = Field(default=None, description="Updated country")
    city: str | None = Field(default=None, description="Updated city")
    metadata: Any | None = Field(default=None, description="Updated metadata")
    status: ScoreStatus | None = Field(
        default=None,
        description="Updated status (admin only: active, under_review, rejected)",
    )
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the score")

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


class ScoreResponse(BaseModel):
    """Response model for a score."""

    id: ScoreID = Field(description="Unique identifier for the score")
    account_id: AccountID = Field(description="ID of the account this score belongs to")
    game_id: GameID = Field(description="ID of the game this score belongs to")
    board_id: BoardID = Field(description="ID of the board this score belongs to")
    identity_id: IdentityID = Field(description="ID of the identity that submitted this score")
    device_id: DeviceID | None = Field(
        default=None, description="ID of the device (deprecated, use identity_id)"
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
    def from_domain(cls, score: Score) -> "ScoreResponse":
        """Convert domain entity to response model.

        Args:
            score: The domain Score entity to convert.

        Returns:
            ScoreResponse with all fields populated from the domain entity.
        """
        # Handle legacy Score entities that may not have identity_id
        identity_id = getattr(score, "identity_id", None)
        if identity_id is None:
            # For legacy scores, create an IdentityID from device_id UUID
            identity_id = IdentityID(score.device_id.uuid)

        return cls(
            id=score.id,
            account_id=score.account_id,
            game_id=score.game_id,
            board_id=score.board_id,
            identity_id=identity_id,
            device_id=score.device_id,
            player_name=score.player_name,
            value=score.value,
            value_display=score.value_display,
            timezone=score.timezone,
            country=score.country,
            city=score.city,
            metadata=score.metadata,
            rank=score.rank,
            is_placeholder=score.is_placeholder,
            is_test=score.is_test,
            status=score.status,
            created_at=score.created_at,
            updated_at=score.updated_at,
        )

    @classmethod
    def from_board_state(
        cls,
        state: BoardState,
        identity: Identity,
        score_event: ScoreEvent,
        rank: int,
    ) -> "ScoreResponse":
        """Convert BoardState to ScoreResponse with masked ID.

        Args:
            state: The BoardState entity representing materialized ranking.
            identity: The Identity entity for player info.
            score_event: The ScoreEvent for metadata (geo, is_test, etc.).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreResponse with ID masked from bst_ to scr_ prefix.
        """
        # Mask BoardStateID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(state.id.uuid)

        return cls(
            id=masked_id,
            account_id=score_event.account_id,
            game_id=score_event.game_id,
            board_id=state.board_id,
            identity_id=identity.id,
            device_id=None,  # Not available from new event-sourced data
            player_name=identity.display_name or "",
            value=state.primary_value or 0.0,
            value_display=None,  # Not stored in board_state
            timezone=score_event.timezone,
            country=score_event.country,
            city=score_event.city,
            metadata=None,  # Not stored in board_state
            rank=rank,
            is_placeholder=False,
            is_test=score_event.is_test,
            status=ScoreStatus.ACTIVE,  # Board states are always active
            created_at=score_event.created_at,
            updated_at=state.updated_at,
        )

    @classmethod
    def from_run_entry(
        cls,
        entry: RunEntry,
        identity: Identity,
        score_event: ScoreEvent,
        rank: int,
    ) -> "ScoreResponse":
        """Convert RunEntry to ScoreResponse with masked ID.

        Args:
            entry: The RunEntry entity representing a single run.
            identity: The Identity entity for player info.
            score_event: The ScoreEvent for metadata (geo, is_test, etc.).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreResponse with ID masked from run_ to scr_ prefix.
        """
        # Mask RunEntryID to ScoreID (same UUID, different prefix)
        masked_id = ScoreID(entry.id.uuid)

        return cls(
            id=masked_id,
            account_id=score_event.account_id,
            game_id=score_event.game_id,
            board_id=entry.board_id,
            identity_id=identity.id,
            device_id=None,  # Not available from new event-sourced data
            player_name=identity.display_name or "",
            value=entry.primary_value,
            value_display=None,  # Not stored in run_entry
            timezone=score_event.timezone,
            country=score_event.country,
            city=score_event.city,
            metadata=None,  # Not stored in run_entry
            rank=rank,
            is_placeholder=False,
            is_test=score_event.is_test,
            status=ScoreStatus.ACTIVE,  # Run entries are always active
            created_at=score_event.created_at,
            updated_at=entry.updated_at,
        )


class ScoreClientResponse(BaseModel):
    """Response model for a score (client API - excludes device_id and geo fields)."""

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
    def from_domain(cls, score: Score) -> "ScoreClientResponse":
        """Convert domain entity to client response model (without device_id or geo fields).

        Args:
            score: The domain Score entity to convert.

        Returns:
            ScoreClientResponse with all fields except device_id, timezone, country, and city.
        """
        # Handle legacy Score entities that may not have identity_id
        identity_id = getattr(score, "identity_id", None)
        if identity_id is None:
            # For legacy scores, create an IdentityID from device_id UUID
            identity_id = IdentityID(score.device_id.uuid)

        return cls(
            id=score.id,
            account_id=score.account_id,
            game_id=score.game_id,
            board_id=score.board_id,
            identity_id=identity_id,
            player_name=score.player_name,
            value=score.value,
            value_display=score.value_display,
            metadata=score.metadata,
            rank=score.rank,
            is_placeholder=score.is_placeholder,
            is_test=score.is_test,
            status=score.status,
            created_at=score.created_at,
            updated_at=score.updated_at,
        )

    @classmethod
    def from_board_state(
        cls,
        state: BoardState,
        identity: Identity,
        score_event: ScoreEvent,
        rank: int,
    ) -> "ScoreClientResponse":
        """Convert BoardState to ScoreClientResponse with masked ID.

        Args:
            state: The BoardState entity representing materialized ranking.
            identity: The Identity entity for player info.
            score_event: The ScoreEvent for metadata (is_test, etc.).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreClientResponse with ID masked from bst_ to scr_ prefix.
        """
        masked_id = ScoreID(state.id.uuid)

        return cls(
            id=masked_id,
            account_id=score_event.account_id,
            game_id=score_event.game_id,
            board_id=state.board_id,
            identity_id=identity.id,
            player_name=identity.display_name or "",
            value=state.primary_value or 0.0,
            value_display=None,
            metadata=None,
            rank=rank,
            is_placeholder=False,
            is_test=score_event.is_test,
            status=ScoreStatus.ACTIVE,
            created_at=score_event.created_at,
            updated_at=state.updated_at,
        )

    @classmethod
    def from_run_entry(
        cls,
        entry: RunEntry,
        identity: Identity,
        score_event: ScoreEvent,
        rank: int,
    ) -> "ScoreClientResponse":
        """Convert RunEntry to ScoreClientResponse with masked ID.

        Args:
            entry: The RunEntry entity representing a single run.
            identity: The Identity entity for player info.
            score_event: The ScoreEvent for metadata (is_test, etc.).
            rank: The computed rank position (1-indexed).

        Returns:
            ScoreClientResponse with ID masked from run_ to scr_ prefix.
        """
        masked_id = ScoreID(entry.id.uuid)

        return cls(
            id=masked_id,
            account_id=score_event.account_id,
            game_id=score_event.game_id,
            board_id=entry.board_id,
            identity_id=identity.id,
            player_name=identity.display_name or "",
            value=entry.primary_value,
            value_display=None,
            metadata=None,
            rank=rank,
            is_placeholder=False,
            is_test=score_event.is_test,
            status=ScoreStatus.ACTIVE,
            created_at=score_event.created_at,
            updated_at=entry.updated_at,
        )
