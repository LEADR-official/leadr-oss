"""Auth ORM models."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.auth.domain.device import Device, DeviceSession, DeviceStatus
from leadr.auth.domain.nonce import Nonce, NonceStatus
from leadr.common.domain.ids import AccountID, DeviceID, DeviceSessionID, GameID, NonceID
from leadr.common.orm import Base

if TYPE_CHECKING:
    from leadr.games.adapters.orm import GameORM


class APIKeyStatusEnum(str, enum.Enum):
    """API Key status enum for database."""

    ACTIVE = "active"
    REVOKED = "revoked"


class APIKeyORM(Base):
    """API Key ORM model.

    Represents an API key for account authentication in the database.
    Maps to the api_keys table with foreign key to accounts and users.
    Each API key is owned by a specific user within the account.
    """

    __tablename__ = "api_keys"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[APIKeyStatusEnum] = mapped_column(
        Enum(
            APIKeyStatusEnum,
            name="api_key_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=APIKeyStatusEnum.ACTIVE,
        server_default="active",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class DeviceStatusEnum(str, enum.Enum):
    """Device status enum for database."""

    ACTIVE = "active"
    BANNED = "banned"
    SUSPENDED = "suspended"


class DeviceORM(Base):
    """Device ORM model.

    Represents a game client device (e.g., mobile device, PC, console) in the database.
    Maps to the devices table with foreign key to games.
    Devices are scoped per-game for client authentication.
    """

    __tablename__ = "devices"

    game_id: Mapped[UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    platform: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    status: Mapped[DeviceStatusEnum] = mapped_column(
        Enum(
            DeviceStatusEnum,
            name="device_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DeviceStatusEnum.ACTIVE,
        server_default="active",
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    device_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # Column name in database
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]
    sessions: Mapped[list["DeviceSessionORM"]] = relationship(
        "DeviceSessionORM",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    nonces: Mapped[list["NonceORM"]] = relationship(
        "NonceORM",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        # Composite unique index on (game_id, device_id)
        Index("ix_devices_game_device", "game_id", "device_id", unique=True),
    )

    @classmethod
    def from_domain(cls, device: Device) -> "DeviceORM":
        """Convert Device domain entity to ORM model."""
        return cls(
            id=device.id.uuid,
            created_at=device.created_at,
            updated_at=device.updated_at,
            deleted_at=device.deleted_at,
            game_id=device.game_id.uuid,
            device_id=device.device_id,
            account_id=device.account_id.uuid,
            platform=device.platform,
            status=DeviceStatusEnum(device.status.value),
            first_seen_at=device.first_seen_at,
            last_seen_at=device.last_seen_at,
            device_metadata=device.metadata,
        )

    def to_domain(self) -> Device:
        """Convert ORM model to Device domain entity."""
        return Device(
            id=DeviceID(self.id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
            game_id=GameID(self.game_id),
            device_id=self.device_id,
            account_id=AccountID(self.account_id),
            platform=self.platform,
            status=DeviceStatus(self.status.value),
            first_seen_at=self.first_seen_at,
            last_seen_at=self.last_seen_at,
            metadata=self.device_metadata,
        )


class DeviceSessionORM(Base):
    """DeviceSession ORM model.

    Represents an active authentication session for a device in the database.
    Maps to the device_sessions table with foreign key to devices.
    Sessions include both access and refresh tokens with token rotation support.
    """

    __tablename__ = "device_sessions"

    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_token_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    refresh_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    device: Mapped["DeviceORM"] = relationship("DeviceORM", back_populates="sessions")

    @classmethod
    def from_domain(cls, session: DeviceSession) -> "DeviceSessionORM":
        """Convert DeviceSession domain entity to ORM model."""
        return cls(
            id=session.id.uuid,
            created_at=session.created_at,
            updated_at=session.updated_at,
            deleted_at=session.deleted_at,
            device_id=session.device_id.uuid,
            access_token_hash=session.access_token_hash,
            refresh_token_hash=session.refresh_token_hash,
            token_version=session.token_version,
            expires_at=session.expires_at,
            refresh_expires_at=session.refresh_expires_at,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            revoked_at=session.revoked_at,
        )

    def to_domain(self) -> DeviceSession:
        """Convert ORM model to DeviceSession domain entity."""
        return DeviceSession(
            id=DeviceSessionID(self.id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
            device_id=DeviceID(self.device_id),
            access_token_hash=self.access_token_hash,
            refresh_token_hash=self.refresh_token_hash,
            token_version=self.token_version,
            expires_at=self.expires_at,
            refresh_expires_at=self.refresh_expires_at,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            revoked_at=self.revoked_at,
        )


class NonceStatusEnum(str, enum.Enum):
    """Nonce status enum for database."""

    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class NonceORM(Base):
    """Nonce ORM model.

    Represents a single-use nonce for replay protection in the database.
    Maps to the nonces table with foreign key to devices.
    Nonces are short-lived tokens (typically 60 seconds) that must be
    obtained before making mutating requests.
    """

    __tablename__ = "nonces"

    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nonce_value: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
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
    status: Mapped[NonceStatusEnum] = mapped_column(
        Enum(
            NonceStatusEnum,
            name="nonce_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=NonceStatusEnum.PENDING,
        server_default="pending",
    )

    # Relationships
    device: Mapped["DeviceORM"] = relationship("DeviceORM", overlaps="nonces")

    @classmethod
    def from_domain(cls, nonce: Nonce) -> "NonceORM":
        """Convert Nonce domain entity to ORM model."""
        return cls(
            id=nonce.id.uuid,
            created_at=nonce.created_at,
            updated_at=nonce.updated_at,
            deleted_at=nonce.deleted_at,
            device_id=nonce.device_id.uuid,
            nonce_value=nonce.nonce_value,
            expires_at=nonce.expires_at,
            used_at=nonce.used_at,
            status=NonceStatusEnum(nonce.status.value),
        )

    def to_domain(self) -> Nonce:
        """Convert ORM model to Nonce domain entity."""
        # Handle both string and enum status values
        status_value = (
            self.status.value if isinstance(self.status, NonceStatusEnum) else self.status
        )
        return Nonce(
            id=NonceID(self.id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
            device_id=DeviceID(self.device_id),
            nonce_value=self.nonce_value,
            expires_at=self.expires_at,
            used_at=self.used_at,
            status=NonceStatus(status_value),
        )
