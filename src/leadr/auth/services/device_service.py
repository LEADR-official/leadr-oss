"""Device authentication service."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.device import Device, DeviceSession
from leadr.auth.services.device_token_crypto import (
    generate_access_token,
    generate_refresh_token,
    hash_token,
    validate_access_token,
    validate_refresh_token,
)
from leadr.auth.services.repositories import DeviceRepository, DeviceSessionRepository
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.services import BaseService
from leadr.config import settings
from leadr.games.adapters.orm import GameORM


class DeviceService(BaseService[Device, DeviceRepository]):
    """Service for device authentication and session management."""

    def __init__(self, session: AsyncSession):
        """Initialize DeviceService.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        super().__init__(session)
        self.session_repo = DeviceSessionRepository(session)

    def _create_repository(self, session: AsyncSession) -> DeviceRepository:
        """Create repository instance."""
        return DeviceRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Device"

    async def start_session(
        self,
        game_id: UUID,
        device_id: str,
        platform: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[Device, str, int]:
        """Start a new device session.

        Creates or updates device, generates JWT access token, and creates session record.
        This is idempotent - calling multiple times updates last_seen_at.

        Args:
            game_id: Game UUID
            device_id: Client-generated device identifier
            platform: Device platform (ios, android, etc.)
            ip_address: Client IP address
            user_agent: Client user agent string
            metadata: Additional device metadata

        Returns:
            tuple[Device, str, int]: (device, access_token_plain, expires_in_seconds)

        Raises:
            EntityNotFoundError: If game doesn't exist
        """
        # Verify game exists and get account_id
        game_orm = await self.session.get(GameORM, game_id)
        if not game_orm:
            raise EntityNotFoundError("Game", str(game_id))

        account_id = game_orm.account_id

        # Get or create device
        device = await self.repository.get_by_game_and_device_id(game_id, device_id)

        if device:
            # Update existing device
            device.update_last_seen()
            if platform and not device.platform:
                device.platform = platform
            device = await self.repository.update(device)
        else:
            # Create new device
            now = datetime.now(UTC)
            device = Device(
                game_id=game_id,
                device_id=device_id,
                account_id=account_id,
                platform=platform,
                first_seen_at=now,
                last_seen_at=now,
                metadata=metadata or {},
            )
            device = await self.repository.create(device)

        # Generate access token
        expires_delta = timedelta(hours=24)  # TODO: Make configurable
        token_plain, token_hash = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=settings.JWT_SECRET,
        )

        # Create session
        session = DeviceSession(
            device_id=device.id,
            access_token_hash=token_hash,
            expires_at=datetime.now(UTC) + expires_delta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.session_repo.create(session)

        expires_in_seconds = int(expires_delta.total_seconds())
        return device, token_plain, expires_in_seconds

    async def validate_device_token(self, token: str) -> Device | None:
        """Validate access token and return associated device.

        Validates JWT signature and expiration, checks session validity,
        and ensures device is active.

        Args:
            token: JWT access token

        Returns:
            Device if token is valid and device is active, None otherwise
        """
        # Validate JWT token
        claims = validate_access_token(token, settings.JWT_SECRET)
        if not claims:
            return None

        # Extract claims
        device_id = claims["sub"]
        game_id = UUID(claims["game_id"])

        # Get device
        device = await self.repository.get_by_game_and_device_id(game_id, device_id)
        if not device:
            return None

        # Check device is active
        if not device.is_active():
            return None

        # Verify session exists and is valid
        token_hash = hash_token(token, settings.JWT_SECRET)
        session = await self.session_repo.get_by_token_hash(token_hash)
        if not session:
            return None

        # Check session validity
        if not session.is_valid():
            return None

        return device

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[str, str, int] | None:
        """Refresh access token using a valid refresh token.

        Validates the refresh token, checks token version for replay attack detection,
        generates new access and refresh tokens with incremented version, and updates
        the session.

        Args:
            refresh_token: JWT refresh token

        Returns:
            tuple[str, str, int]: (access_token_plain, refresh_token_plain, expires_in_seconds)
            or None if refresh token is invalid

        Token Rotation Security:
            - The token_version in the JWT must match the session's token_version
            - When tokens are refreshed, the version is incremented
            - Old refresh tokens with lower versions are rejected (prevents replay attacks)
        """
        # Validate refresh JWT token
        claims = validate_refresh_token(refresh_token, settings.JWT_SECRET)
        if not claims:
            return None

        # Hash the refresh token and look up session
        refresh_token_hash = hash_token(refresh_token, settings.JWT_SECRET)
        session = await self.session_repo.get_by_refresh_token_hash(refresh_token_hash)
        if not session:
            return None

        # Verify token version matches (replay attack detection)
        jwt_version = claims["token_version"]
        if jwt_version != session.token_version:
            return None

        # Check that refresh token is not expired
        if session.is_refresh_expired():
            return None

        # Check that session is not revoked
        if session.is_revoked():
            return None

        # Extract claims for token generation
        device_id = claims["sub"]
        game_id = UUID(claims["game_id"])
        account_id = UUID(claims["account_id"])

        # Generate new access token
        access_expires_delta = timedelta(hours=24)  # TODO: Make configurable
        access_token_plain, access_token_hash = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=access_expires_delta,
            secret=settings.JWT_SECRET,
        )

        # Generate new refresh token with incremented version
        refresh_expires_delta = timedelta(days=30)  # TODO: Make configurable
        new_refresh_token_plain, new_refresh_token_hash = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=session.token_version + 1,
            expires_delta=refresh_expires_delta,
            secret=settings.JWT_SECRET,
        )

        # Update session with new tokens and incremented version
        session.access_token_hash = access_token_hash
        session.refresh_token_hash = new_refresh_token_hash
        session.rotate_tokens()  # Increments token_version
        session.expires_at = datetime.now(UTC) + access_expires_delta
        session.refresh_expires_at = datetime.now(UTC) + refresh_expires_delta
        await self.session_repo.update(session)

        expires_in_seconds = int(access_expires_delta.total_seconds())
        return access_token_plain, new_refresh_token_plain, expires_in_seconds
