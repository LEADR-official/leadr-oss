"""Jam code redemption domain models for tracking code usage."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from leadr.common.domain.ids import AccountID
from leadr.common.domain.models import Entity


class JamCodeRedemption(Entity):
    """Jam code redemption domain entity.

    Represents a single use of a jam code during account registration.
    Tracks which account redeemed which code, when it was redeemed,
    and any associated metadata (e.g., CLI configuration, user agent).
    """

    jam_code_id: UUID = Field(description="ID of the jam code that was redeemed")
    account_id: AccountID = Field(description="ID of the account that redeemed the code")
    redeemed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the code was redeemed (UTC)",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the redemption (e.g., CLI config, user agent)",
    )

    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get a metadata value from the meta dictionary.

        Args:
            key: The metadata key to retrieve.
            default: Default value if the key doesn't exist.

        Returns:
            The metadata value or the default.
        """
        return self.meta.get(key, default)
