"""API schemas for registration endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from leadr.common.domain.ids import AccountID, JamCodeID, JamCodeRedemptionID

# Public Registration Schemas


class InitiateRegistrationRequest(BaseModel):
    """Request to initiate registration by sending verification code."""

    email: EmailStr = Field(description="Email address to send verification code to")


class InitiateRegistrationResponse(BaseModel):
    """Response after initiating registration."""

    message: str = Field(description="Success message")
    code_expires_in: int = Field(description="Seconds until the code expires")


class VerifyCodeRequest(BaseModel):
    """Request to verify an email verification code."""

    email: EmailStr = Field(description="Email address")
    code: str = Field(description="6-character verification code", min_length=6, max_length=6)


class VerifyCodeResponse(BaseModel):
    """Response after verifying a code."""

    verification_token: str = Field(description="Temporary token for completing registration")
    expires_in: int = Field(description="Seconds until the token expires")


class CompleteRegistrationRequest(BaseModel):
    """Request to complete registration and create account."""

    verification_token: str = Field(description="Token from code verification step")
    account_name: str = Field(description="Name for the new account", min_length=1, max_length=100)
    account_slug: str | None = Field(
        default=None, description="Optional URL slug (auto-generated if not provided)"
    )
    jam_code: str | None = Field(default=None, description="Optional jam/promo code")
    display_name: str | None = Field(
        default=None,
        description="Optional display name for user (auto-generated from email if not provided)",
    )

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        """Convert empty/whitespace strings to None."""
        if value is not None and not value.strip():
            return None
        return value


class CompleteRegistrationResponse(BaseModel):
    """Response after completing registration."""

    account_id: AccountID = Field(description="ID of the created account")
    account_slug: str = Field(description="URL slug of the account")
    api_key: str = Field(description="API key for authentication")
    display_name: str = Field(description="Display name of the created user")

    @classmethod
    def from_domain(cls, account, user, api_key: str) -> "CompleteRegistrationResponse":
        """Create response from domain entities.

        Args:
            account: Account domain entity.
            user: User domain entity.
            api_key: API key string.

        Returns:
            CompleteRegistrationResponse instance.
        """
        return cls(
            account_id=account.id.uuid,
            account_slug=account.slug,
            api_key=api_key,
            display_name=user.display_name,
        )


# Admin Jam Code Management Schemas


class CreateJamCodeRequest(BaseModel):
    """Request to create a new jam code."""

    code: str = Field(
        description="Alphanumeric code (3-50 characters)", min_length=3, max_length=50
    )
    description: str = Field(description="Human-readable description")
    features: dict = Field(default_factory=dict, description="Features/config for this code")
    max_uses: int | None = Field(default=None, description="Maximum redemptions (null = unlimited)")
    expires_at: datetime | None = Field(default=None, description="Expiration date (null = never)")


class UpdateJamCodeRequest(BaseModel):
    """Request to update a jam code."""

    description: str | None = Field(default=None, description="New description")
    features: dict | None = Field(default=None, description="New features/config")
    max_uses: int | None = Field(default=None, description="New max uses")
    active: bool | None = Field(default=None, description="New active status")
    expires_at: datetime | None = Field(default=None, description="New expiration date")


class JamCodeResponse(BaseModel):
    """Response representing a jam code."""

    id: JamCodeID
    code: str
    description: str
    features: dict
    max_uses: int | None
    current_uses: int
    active: bool
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, jam_code) -> "JamCodeResponse":
        """Create response from domain entity.

        Args:
            jam_code: JamCode domain entity.

        Returns:
            JamCodeResponse instance.
        """
        return cls(
            id=jam_code.id,
            code=jam_code.code,
            description=jam_code.description,
            features=jam_code.features,
            max_uses=jam_code.max_uses,
            current_uses=jam_code.current_uses,
            active=jam_code.active,
            expires_at=jam_code.expires_at,
            created_at=jam_code.created_at,
            updated_at=jam_code.updated_at,
        )


class JamCodeRedemptionResponse(BaseModel):
    """Response representing a jam code redemption."""

    id: JamCodeRedemptionID
    jam_code_id: JamCodeID
    account_id: AccountID
    redeemed_at: datetime
    meta: dict

    @classmethod
    def from_domain(cls, redemption) -> "JamCodeRedemptionResponse":
        """Create response from domain entity.

        Args:
            redemption: JamCodeRedemption domain entity.

        Returns:
            JamCodeRedemptionResponse instance.
        """
        return cls(
            id=redemption.id,
            jam_code_id=redemption.jam_code_id,
            account_id=redemption.account_id.uuid,
            redeemed_at=redemption.redeemed_at,
            meta=redemption.meta,
        )
