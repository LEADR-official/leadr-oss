"""Registration ORM models."""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.orm import Base
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption
from leadr.registration.domain.verification_code import (
    VerificationCode,
    VerificationCodeStatus,
    VerificationCodeType,
)


class VerificationCodeStatusEnum(str, enum.Enum):
    """Verification code status enum for database."""

    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class VerificationCodeTypeEnum(str, enum.Enum):
    """Verification code type enum for database."""

    REGISTRATION = "REGISTRATION"
    INVITE = "INVITE"


class VerificationCodeORM(Base):
    """Verification Code ORM model.

    Represents an email verification code in the database.
    Maps to the verification_codes table.
    Used during account registration to verify email ownership.
    """

    __tablename__ = "verification_codes"

    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    status: Mapped[VerificationCodeStatusEnum] = mapped_column(
        Enum(
            VerificationCodeStatusEnum,
            name="verification_code_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=VerificationCodeStatusEnum.PENDING,
        server_default="pending",
    )
    code_type: Mapped[VerificationCodeTypeEnum] = mapped_column(
        Enum(
            VerificationCodeTypeEnum,
            name="verification_code_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=VerificationCodeTypeEnum.REGISTRATION,
        server_default="REGISTRATION",
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_verification_codes_email_status", "email", "status"),
        Index("ix_verification_codes_type_user_id", "code_type", "user_id"),
    )

    @classmethod
    def from_domain(cls, domain: VerificationCode) -> "VerificationCodeORM":
        """Convert domain entity to ORM model.

        Args:
            domain: The domain entity to convert.

        Returns:
            The ORM model instance.
        """
        return cls(
            id=domain.id,
            email=domain.email,
            code=domain.code,
            status=VerificationCodeStatusEnum(domain.status.value),
            code_type=VerificationCodeTypeEnum(domain.code_type.value),
            user_id=domain.user_id.uuid if domain.user_id else None,
            expires_at=domain.expires_at,
            used_at=domain.used_at,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            deleted_at=domain.deleted_at,
        )

    def to_domain(self) -> VerificationCode:
        """Convert ORM model to domain entity.

        Returns:
            The domain entity instance.
        """
        from leadr.common.domain.ids import UserID

        return VerificationCode(
            id=self.id,
            email=self.email,
            code=self.code,
            status=VerificationCodeStatus(self.status.value),
            code_type=VerificationCodeType(self.code_type.value),
            user_id=UserID(self.user_id) if self.user_id else None,
            expires_at=self.expires_at,
            used_at=self.used_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )


class JamCodeORM(Base):
    """Jam Code ORM model.

    Represents a promotional code in the database.
    Maps to the jam_codes table.
    Used for tracking game jam codes, marketing campaigns, and referrals.
    """

    __tablename__ = "jam_codes"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={},
        server_default="{}",
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (Index("ix_jam_codes_active_expires", "active", "expires_at"),)

    @classmethod
    def from_domain(cls, domain: JamCode) -> "JamCodeORM":
        """Convert domain entity to ORM model.

        Args:
            domain: The domain entity to convert.

        Returns:
            The ORM model instance.
        """
        return cls(
            id=domain.id,
            code=domain.code,
            description=domain.description,
            features=domain.features,
            max_uses=domain.max_uses,
            current_uses=domain.current_uses,
            active=domain.active,
            expires_at=domain.expires_at,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            deleted_at=domain.deleted_at,
        )

    def to_domain(self) -> JamCode:
        """Convert ORM model to domain entity.

        Returns:
            The domain entity instance.
        """
        return JamCode(
            id=self.id,
            code=self.code,
            description=self.description,
            features=self.features,
            max_uses=self.max_uses,
            current_uses=self.current_uses,
            active=self.active,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )


class JamCodeRedemptionORM(Base):
    """Jam Code Redemption ORM model.

    Represents a single use of a jam code during registration.
    Maps to the jam_code_redemptions table with foreign keys to jam_codes and accounts.
    Tracks which account redeemed which code and when.
    """

    __tablename__ = "jam_code_redemptions"

    jam_code_id: Mapped[UUID] = mapped_column(
        ForeignKey("jam_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={},
        server_default="{}",
    )

    __table_args__ = (
        Index("ix_jam_code_redemptions_jam_code_account", "jam_code_id", "account_id"),
    )

    @classmethod
    def from_domain(cls, domain: JamCodeRedemption) -> "JamCodeRedemptionORM":
        """Convert domain entity to ORM model.

        Args:
            domain: The domain entity to convert.

        Returns:
            The ORM model instance.
        """
        return cls(
            id=domain.id,
            jam_code_id=domain.jam_code_id,
            account_id=domain.account_id.uuid,
            redeemed_at=domain.redeemed_at,
            meta=domain.meta,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            deleted_at=domain.deleted_at,
        )

    def to_domain(self) -> JamCodeRedemption:
        """Convert ORM model to domain entity.

        Returns:
            The domain entity instance.
        """
        from leadr.common.domain.ids import AccountID

        return JamCodeRedemption(
            id=self.id,
            jam_code_id=self.jam_code_id,
            account_id=AccountID(self.account_id),
            redeemed_at=self.redeemed_at,
            meta=self.meta,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )
