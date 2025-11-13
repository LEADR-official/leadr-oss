"""Prefixed ID types for entity identification."""

from typing import Self
from uuid import UUID, uuid4


class PrefixedID:
    """Base class for entity IDs with type prefixes.

    Provides Stripe-style prefixed UUIDs (e.g., "acc_123e4567-e89b-...") while
    maintaining internal UUID representation for database efficiency.

    Usage:
        - AccountID() → generates new ID
        - AccountID("acc_123...") → parses prefixed string
        - AccountID(uuid_obj) → wraps existing UUID
    """

    prefix: str = ""  # Override in subclasses

    def __init__(self, value: str | UUID | Self | None = None) -> None:
        """Initialize a prefixed ID.

        Args:
            value: Optional value to initialize from:
                - None: Generate new UUID
                - str: Parse "prefix_uuid" format
                - UUID: Wrap existing UUID
                - PrefixedID: Extract UUID from another PrefixedID

        Raises:
            ValueError: If string format is invalid or prefix doesn't match
        """
        if value is None:
            self.uuid = uuid4()
        elif isinstance(value, str):
            self._parse_from_string(value)
        elif isinstance(value, UUID):
            self.uuid = value
        elif isinstance(value, PrefixedID):
            self.uuid = value.uuid
        else:
            raise TypeError(f"Invalid type for {self.__class__.__name__}: {type(value)}")

    def _parse_from_string(self, value: str) -> None:
        """Parse prefixed ID string into UUID.

        Args:
            value: String in format "prefix_uuid"

        Raises:
            ValueError: If format is invalid or prefix doesn't match
        """
        if "_" not in value:
            raise ValueError(
                f"Invalid {self.__class__.__name__} format: expected 'prefix_uuid', got '{value}'"
            )

        prefix, uuid_str = value.split("_", 1)

        if prefix != self.prefix:
            raise ValueError(
                f"Invalid prefix for {self.__class__.__name__}: "
                f"expected '{self.prefix}', got '{prefix}'"
            )

        try:
            self.uuid = UUID(uuid_str)
        except ValueError as e:
            raise ValueError(f"Invalid UUID in {self.__class__.__name__}: '{uuid_str}'") from e

    def __str__(self) -> str:
        """Return string representation in 'prefix_uuid' format."""
        return f"{self.prefix}_{self.uuid}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{self.__class__.__name__}('{self}')"

    def __eq__(self, other: object) -> bool:
        """Check equality based on UUID and type.

        Supports comparison with:
        - Same PrefixedID type (compares UUIDs)
        - UUID objects (compares UUID values)
        - Strings (parses and compares)
        """
        if isinstance(other, self.__class__):
            return self.uuid == other.uuid
        if isinstance(other, UUID):
            return self.uuid == other
        if isinstance(other, str):
            try:
                parsed = self.__class__(other)
                return self.uuid == parsed.uuid
            except (ValueError, TypeError):
                return False
        return False

    def __hash__(self) -> int:
        """Make ID hashable for use in sets/dicts."""
        return hash((self.__class__, self.uuid))

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 schema for serialization/validation."""
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.union_schema(
                [
                    core_schema.str_schema(),
                    core_schema.is_instance_schema(UUID),
                    core_schema.is_instance_schema(cls),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: str(instance),
            ),
        )

    @classmethod
    def _validate(cls, value: str | UUID | Self | object) -> Self:
        """Validate and convert value for Pydantic."""
        if isinstance(value, cls):
            return value
        # Cast to expected types - Pydantic schema ensures only valid types reach here
        if isinstance(value, str | UUID):
            return cls(value)
        # This should never happen due to schema validation, but type checker needs it
        return cls(value)  # type: ignore[arg-type]


# Entity-specific ID types


class AccountID(PrefixedID):
    """Account entity identifier."""

    prefix = "acc"


class UserID(PrefixedID):
    """User entity identifier."""

    prefix = "usr"


class GameID(PrefixedID):
    """Game entity identifier."""

    prefix = "gam"


class BoardID(PrefixedID):
    """Board entity identifier."""

    prefix = "brd"


class BoardTemplateID(PrefixedID):
    """Board template entity identifier."""

    prefix = "tpl"


class ScoreID(PrefixedID):
    """Score entity identifier."""

    prefix = "scr"


class APIKeyID(PrefixedID):
    """API key entity identifier."""

    prefix = "key"


class DeviceID(PrefixedID):
    """Device entity identifier."""

    prefix = "dev"


class DeviceSessionID(PrefixedID):
    """Device session entity identifier."""

    prefix = "ses"


class NonceID(PrefixedID):
    """Nonce entity identifier."""

    prefix = "non"


class ScoreSubmissionMetaID(PrefixedID):
    """Score submission metadata entity identifier."""

    prefix = "sub"


class ScoreFlagID(PrefixedID):
    """Score flag entity identifier."""

    prefix = "flg"
