"""Score domain entity."""

import json
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity
from leadr.config import settings


class Score(Entity):
    """
    Score represents a player's score submission for a board.

    Scores are immutable in terms of their associations (account, game, board, device)
    but mutable in terms of their value and metadata for corrections/updates.
    """

    account_id: UUID = Field(
        frozen=True, description="ID of the account this score belongs to (immutable)"
    )
    game_id: UUID = Field(
        frozen=True, description="ID of the game this score belongs to (immutable)"
    )
    board_id: UUID = Field(
        frozen=True, description="ID of the board this score belongs to (immutable)"
    )
    device_id: UUID = Field(
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

    @field_validator("player_name")
    @classmethod
    def validate_player_name(cls, v: str) -> str:
        """Validate that player_name is not empty and strip whitespace.

        Args:
            v: The player_name to validate.

        Returns:
            The validated and trimmed player_name.

        Raises:
            ValueError: If player_name is empty or whitespace only.
        """
        v = v.strip()
        if not v:
            raise ValueError("player_name cannot be empty")
        return v

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
