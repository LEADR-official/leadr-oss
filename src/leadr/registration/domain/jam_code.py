"""Jam code domain models for promotional codes and special features."""

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity


class JamCode(Entity):
    """Jam code domain entity.

    Represents a promotional code that grants special features or access during registration.
    Codes can be used for game jams, marketing campaigns, or referral tracking.
    Supports optional usage limits, expiration dates, and custom feature flags stored as JSON.
    """

    code: str = Field(
        description="Alphanumeric code (3-50 characters, case-insensitive)",
        min_length=3,
        max_length=50,
    )
    description: str = Field(description="Human-readable description of this code's purpose")
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom features/config for this code (e.g., CLI templates, score limits)",
    )
    max_uses: int | None = Field(
        default=None,
        description="Maximum number of redemptions allowed (None = unlimited)",
    )
    current_uses: int = Field(
        default=0,
        description="Current number of times this code has been redeemed",
    )
    active: bool = Field(
        default=True,
        description="Whether this code can currently be redeemed",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When this code expires (None = never expires)",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate and normalize the jam code.

        Args:
            v: The code value to validate.

        Returns:
            The normalized (uppercase) code.

        Raises:
            ValueError: If the code contains non-alphanumeric characters.
        """
        if not re.match(r"^[a-zA-Z0-9]+$", v):
            raise ValueError("code must contain only alphanumeric characters")
        return v.upper()  # Normalize to uppercase

    def is_expired(self) -> bool:
        """Check if the jam code has expired.

        Returns:
            True if the code has an expiration date and it has passed.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def has_uses_remaining(self) -> bool:
        """Check if the jam code has remaining uses.

        Returns:
            True if the code has no usage limit or has not reached its limit.
        """
        if self.max_uses is None:
            return True  # Unlimited uses
        return self.current_uses < self.max_uses

    def is_valid(self) -> bool:
        """Check if the jam code is valid and can be redeemed.

        A code is valid if it's active, not expired, and has uses remaining.

        Returns:
            True if the code can be used for registration.
        """
        return self.active and not self.is_expired() and self.has_uses_remaining()

    def increment_uses(self) -> None:
        """Increment the usage count by one.

        Called when a jam code is successfully redeemed during registration.
        """
        self.current_uses += 1

    def deactivate(self) -> None:
        """Deactivate the jam code, preventing further redemptions.

        Used to manually disable a code (e.g., if it's compromised or no longer needed).
        """
        self.active = False

    def activate(self) -> None:
        """Activate the jam code, allowing redemptions.

        Used to re-enable a previously deactivated code.
        """
        self.active = True

    def get_feature(self, key: str, default: Any = None) -> Any:
        """Get a feature value from the features dictionary.

        Args:
            key: The feature key to retrieve.
            default: Default value if the key doesn't exist.

        Returns:
            The feature value or the default.
        """
        return self.features.get(key, default)
