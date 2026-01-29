"""Device authentication service."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.device import Device
from leadr.auth.services.repositories import DeviceRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, DeviceID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.games.adapters.orm import GameORM


class DeviceService(BaseService[Device, DeviceRepository]):
    """Service for device management.

    Devices are internal lookup tables that map client fingerprints to games/accounts.
    For session management, use IdentityService instead.
    """

    def __init__(self, session: AsyncSession):
        """Initialize DeviceService.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        super().__init__(session)

    def _create_repository(self, session: AsyncSession) -> DeviceRepository:
        """Create repository instance."""
        return DeviceRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Device"

    async def get_or_create_device(
        self,
        game_id: GameID,
        client_fingerprint: str,
        platform: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Device:
        """Get or create a device record.

        This is used as an internal lookup table to map fingerprints to games/accounts.
        Does NOT create sessions - use IdentityService.start_session() for that.

        Args:
            game_id: Game UUID
            client_fingerprint: Client-generated SHA256 device fingerprint
            platform: Device platform (ios, android, etc.)
            metadata: Additional device metadata

        Returns:
            Device: The device record (new or existing)

        Raises:
            EntityNotFoundError: If game doesn't exist
        """
        # Verify game exists and get account_id
        game_uuid = game_id.uuid if hasattr(game_id, "uuid") else game_id
        game_orm = await self.session.get(GameORM, game_uuid)
        if not game_orm:
            raise EntityNotFoundError("Game", str(game_id))

        account_id = AccountID(game_orm.account_id)

        # Get or create device
        device = await self.repository.get_by_game_and_fingerprint(game_id, client_fingerprint)

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
                client_fingerprint=client_fingerprint,
                account_id=account_id,
                platform=platform,
                first_seen_at=now,
                last_seen_at=now,
                metadata=metadata or {},
            )
            device = await self.repository.create(device)

        return device

    async def list_devices(
        self,
        account_id: AccountID | None,
        *,
        game_id: GameID | None = None,
        status: str | None = None,
        pagination: PaginationParams,
    ) -> PaginatedResult[Device]:
        """List devices for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all devices
                (superadmin use case).
            game_id: Optional game ID to filter by
            status: Optional status to filter by (active, banned, suspended)
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing Device entities.

        Example:
            >>> devices = await service.list_devices(
            ...     account_id=account.id,
            ...     status="active",
            ...     pagination=pagination,
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            game_id=game_id,
            status=status,
            pagination=pagination,
        )

    async def get_device(self, device_id: UUID) -> Device | None:
        """Get a device by its ID.

        Args:
            device_id: The ID of the device to retrieve

        Returns:
            The device if found, None otherwise

        Example:
            >>> device = await service.get_device(device_id)
        """
        return await self.get_by_id(device_id)

    async def ban_device(self, device_id: DeviceID) -> Device:
        """Ban a device, preventing further authentication.

        Args:
            device_id: The ID of the device to ban

        Returns:
            The updated device

        Raises:
            EntityNotFoundError: If the device doesn't exist

        Example:
            >>> device = await service.ban_device(device_id)
        """
        device = await self.get_by_id_or_raise(device_id)
        device.ban()
        return await self.repository.update(device)

    async def suspend_device(self, device_id: DeviceID) -> Device:
        """Suspend a device temporarily.

        Args:
            device_id: The ID of the device to suspend

        Returns:
            The updated device

        Raises:
            EntityNotFoundError: If the device doesn't exist

        Example:
            >>> device = await service.suspend_device(device_id)
        """
        device = await self.get_by_id_or_raise(device_id)
        device.suspend()
        return await self.repository.update(device)

    async def activate_device(self, device_id: DeviceID) -> Device:
        """Activate a device, allowing authentication.

        Args:
            device_id: The ID of the device to activate

        Returns:
            The updated device

        Raises:
            EntityNotFoundError: If the device doesn't exist

        Example:
            >>> device = await service.activate_device(device_id)
        """
        device = await self.get_by_id_or_raise(device_id)
        device.activate()
        return await self.repository.update(device)
