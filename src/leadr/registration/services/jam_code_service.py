"""Jam code service for managing promotional codes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption
from leadr.registration.services.repositories import JamCodeRedemptionRepository, JamCodeRepository


class JamCodeService:
    """Service for managing jam codes and redemptions."""

    def __init__(self, db: AsyncSession):
        """Initialize the jam code service.

        Args:
            db: Database session.
        """
        self.db = db
        self.jam_code_repository = JamCodeRepository(db)
        self.redemption_repository = JamCodeRedemptionRepository(db)

    async def validate_and_get_jam_code(self, code: str) -> JamCode | None:
        """Validate a jam code and return it if valid.

        Args:
            code: The jam code to validate.

        Returns:
            The jam code if valid, None if invalid or not found.
        """
        jam_code = await self.jam_code_repository.find_by_code(code)

        if not jam_code:
            return None

        if not jam_code.is_valid():
            return None

        return jam_code

    async def redeem_jam_code(
        self,
        jam_code: JamCode,
        account_id: AccountID,
        meta: dict | None = None,
    ) -> JamCodeRedemption:
        """Redeem a jam code for an account.

        Args:
            jam_code: The jam code to redeem.
            account_id: The account redeeming the code.
            meta: Optional metadata to store with the redemption.

        Returns:
            The jam code redemption entity.

        Raises:
            ValueError: If the jam code has already been redeemed by this account.
        """
        # Check if account has already redeemed this code
        has_redeemed = await self.redemption_repository.has_redeemed(account_id, jam_code.id)
        if has_redeemed:
            raise ValueError("This account has already redeemed this jam code")

        # Increment usage count
        jam_code.increment_uses()
        await self.jam_code_repository.update(jam_code)

        # Create redemption record
        redemption = JamCodeRedemption(
            jam_code_id=jam_code.id,
            account_id=account_id,
            meta=meta or {},
        )
        await self.redemption_repository.create(redemption)
        await self.db.commit()

        return redemption

    async def create_jam_code(
        self,
        code: str,
        description: str,
        features: dict | None = None,
        max_uses: int | None = None,
        expires_at: datetime | None = None,
    ) -> JamCode:
        """Create a new jam code.

        Args:
            code: The code value (will be normalized to uppercase).
            description: Human-readable description.
            features: Optional features dictionary.
            max_uses: Optional maximum number of redemptions.
            expires_at: Optional expiration date.

        Returns:
            The created jam code.

        Raises:
            ValueError: If a jam code with this code already exists.
        """
        # Check if code already exists
        existing = await self.jam_code_repository.find_by_code(code)
        if existing:
            raise ValueError(f"Jam code '{code}' already exists")

        jam_code = JamCode(
            code=code,
            description=description,
            features=features or {},
            max_uses=max_uses,
            expires_at=expires_at,
        )

        await self.jam_code_repository.create(jam_code)
        await self.db.commit()

        return jam_code

    async def get_jam_code_by_id(self, jam_code_id: UUID) -> JamCode | None:
        """Get a jam code by its ID.

        Args:
            jam_code_id: The jam code ID.

        Returns:
            The jam code if found, None otherwise.
        """
        return await self.jam_code_repository.get_by_id(jam_code_id)

    async def list_jam_codes(
        self,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[JamCode]:
        """List all jam codes with pagination.

        Args:
            pagination: Pagination parameters.

        Returns:
            Paginated result of jam codes.
        """
        return await self.jam_code_repository.filter(pagination=pagination)

    async def update_jam_code(
        self,
        jam_code_id: UUID,
        description: str | None = None,
        features: dict | None = None,
        max_uses: int | None = None,
        active: bool | None = None,
        expires_at: datetime | None = None,
    ) -> JamCode:
        """Update a jam code.

        Args:
            jam_code_id: The jam code ID.
            description: Optional new description.
            features: Optional new features dictionary.
            max_uses: Optional new max uses.
            active: Optional new active status.
            expires_at: Optional new expiration date.

        Returns:
            The updated jam code.

        Raises:
            ValueError: If the jam code doesn't exist.
        """
        jam_code = await self.jam_code_repository.get_by_id(jam_code_id)
        if not jam_code:
            raise ValueError("Jam code not found")

        if description is not None:
            jam_code.description = description
        if features is not None:
            jam_code.features = features
        if max_uses is not None:
            jam_code.max_uses = max_uses
        if active is not None:
            if active:
                jam_code.activate()
            else:
                jam_code.deactivate()
        if expires_at is not None:
            jam_code.expires_at = expires_at

        await self.jam_code_repository.update(jam_code)
        await self.db.commit()

        return jam_code
