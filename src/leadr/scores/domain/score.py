"""Score domain entity."""

import json
from typing import Any

from pydantic import Field, field_validator, model_validator

from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.common.domain.models import Entity
from leadr.config import settings
from leadr.scores.domain.anti_cheat.enums import ScoreStatus


class Score(Entity):
    """
    Score represents a player's score submission for a board.

    Scores are immutable in terms of their associations (account, game, board, device)
    but mutable in terms of their value and metadata for corrections/updates.
    """

    id: ScoreID = Field(
        frozen=True,
        default_factory=ScoreID,
        description="Unique score identifier",
    )
    account_id: AccountID = Field(
        frozen=True, description="ID of the account this score belongs to (immutable)"
    )
    game_id: GameID = Field(
        frozen=True, description="ID of the game this score belongs to (immutable)"
    )
    board_id: BoardID = Field(
        frozen=True, description="ID of the board this score belongs to (immutable)"
    )
    device_id: DeviceID = Field(
        frozen=True, description="ID of the device that submitted this score (immutable)"
    )
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score for sorting/comparison")
    value_display: str | None = Field(
        default=None,
        description="Optional formatted display string (e.g., '1:23.45', '1,234 points')",
    )
    timezone: str | None = Field(
        default=None, description="Optional timezone filter for score categorization"
    )
    country: str | None = Field(
        default=None, description="Optional country filter for score categorization"
    )
    city: str | None = Field(
        default=None, description="Optional city filter for score categorization"
    )
    metadata: Any | None = Field(
        default=None,
        description="Optional JSON metadata for game-specific data (loadouts, seeds, etc.)",
    )
    rank: int | None = Field(
        default=None,
        description="Position in leaderboard (1 = first place). "
        "Populated when querying with board_id.",
    )
    is_placeholder: bool = Field(
        default=False,
        description="True if this is a synthetic placeholder score (from around_score_value query)",
    )
    is_test: bool = Field(
        default=False,
        description="True if score was submitted in test mode",
    )
    status: ScoreStatus = Field(
        default=ScoreStatus.PROVISIONAL,
        description="Lifecycle status (provisional, active, under_review, rejected)",
    )

    @field_validator("player_name")
    @classmethod
    def strip_player_name(cls, v: str) -> str:
        """Strip whitespace from player_name.

        Args:
            v: The player_name to validate.

        Returns:
            The trimmed player_name.
        """
        return v.strip()

    @model_validator(mode="after")
    def validate_player_name_not_empty(self) -> "Score":
        """Validate that player_name is not empty for non-placeholder scores.

        Placeholder scores are allowed to have empty player_name since they
        are synthetic scores created for around_score_value queries.

        Returns:
            The validated Score instance.

        Raises:
            ValueError: If player_name is empty and this is not a placeholder.
        """
        if not self.is_placeholder and not self.player_name:
            raise ValueError("player_name cannot be empty")
        return self

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, v: Any) -> Any:
        """Validate that metadata does not exceed size limit.

        Args:
            v: The metadata to validate.

        Returns:
            The validated metadata.

        Raises:
            ValueError: If metadata exceeds the configured size limit.
        """
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

    def activate(self) -> None:
        """Mark score as active (passed anti-cheat)."""
        self.status = ScoreStatus.ACTIVE

    def flag_for_review(self) -> None:
        """Mark score as under review (flagged by anti-cheat)."""
        self.status = ScoreStatus.UNDER_REVIEW

    def reject(self) -> None:
        """Mark score as rejected (confirmed cheating)."""
        self.status = ScoreStatus.REJECTED
