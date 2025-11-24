"""Registration repository services for verification codes and jam codes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from leadr.common.domain.ids import AccountID
from leadr.common.repositories import BaseRepository
from leadr.registration.adapters.orm import (
    JamCodeORM,
    JamCodeRedemptionORM,
    VerificationCodeORM,
    VerificationCodeStatusEnum,
)
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption
from leadr.registration.domain.verification_code import VerificationCode


class VerificationCodeRepository(BaseRepository[VerificationCode, VerificationCodeORM]):
    """Verification code repository for managing email verification codes."""

    def _to_domain(self, orm: VerificationCodeORM) -> VerificationCode:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: VerificationCode) -> VerificationCodeORM:
        """Convert domain entity to ORM model."""
        return VerificationCodeORM.from_domain(entity)

    def _get_orm_class(self) -> type[VerificationCodeORM]:
        """Get the ORM model class."""
        return VerificationCodeORM

    async def find_valid_code_by_email(self, email: str, code: str) -> VerificationCode | None:
        """Find a valid (pending) verification code by email and code value.

        Args:
            email: The email address.
            code: The verification code.

        Returns:
            The verification code if found and valid, None otherwise.
        """
        query = select(VerificationCodeORM).where(
            VerificationCodeORM.email == email,
            VerificationCodeORM.code == code.upper(),
            VerificationCodeORM.status == VerificationCodeStatusEnum.PENDING,
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def invalidate_codes_for_email(self, email: str) -> None:
        """Mark all pending verification codes for an email as expired.

        Used when generating a new code to invalidate previous ones.

        Args:
            email: The email address.
        """
        query = (
            select(VerificationCodeORM)
            .where(
                VerificationCodeORM.email == email,
                VerificationCodeORM.status == VerificationCodeStatusEnum.PENDING,
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        codes = result.scalars().all()

        for code_orm in codes:
            code_orm.status = VerificationCodeStatusEnum.EXPIRED

        await self.db.flush()


class JamCodeRepository(BaseRepository[JamCode, JamCodeORM]):
    """Jam code repository for managing promotional codes."""

    def _to_domain(self, orm: JamCodeORM) -> JamCode:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: JamCode) -> JamCodeORM:
        """Convert domain entity to ORM model."""
        return JamCodeORM.from_domain(entity)

    def _get_orm_class(self) -> type[JamCodeORM]:
        """Get the ORM model class."""
        return JamCodeORM

    async def find_by_code(self, code: str) -> JamCode | None:
        """Find a jam code by its code value.

        Args:
            code: The jam code to look up (case-insensitive).

        Returns:
            The jam code if found, None otherwise.
        """
        query = select(JamCodeORM).where(JamCodeORM.code == code.upper())
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None


class JamCodeRedemptionRepository(BaseRepository[JamCodeRedemption, JamCodeRedemptionORM]):
    """Jam code redemption repository for tracking code usage."""

    def _to_domain(self, orm: JamCodeRedemptionORM) -> JamCodeRedemption:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: JamCodeRedemption) -> JamCodeRedemptionORM:
        """Convert domain entity to ORM model."""
        return JamCodeRedemptionORM.from_domain(entity)

    def _get_orm_class(self) -> type[JamCodeRedemptionORM]:
        """Get the ORM model class."""
        return JamCodeRedemptionORM

    async def find_by_account(self, account_id: AccountID) -> list[JamCodeRedemption]:
        """Find all jam code redemptions for an account.

        Args:
            account_id: The account ID.

        Returns:
            List of redemptions for the account.
        """
        query = select(JamCodeRedemptionORM).where(
            JamCodeRedemptionORM.account_id == account_id.uuid
        )
        result = await self.db.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def has_redeemed(self, account_id: AccountID, jam_code_id: UUID) -> bool:
        """Check if an account has already redeemed a specific jam code.

        Args:
            account_id: The account ID.
            jam_code_id: The jam code ID.

        Returns:
            True if the account has redeemed this code, False otherwise.
        """
        query = select(JamCodeRedemptionORM).where(
            JamCodeRedemptionORM.account_id == account_id.uuid,
            JamCodeRedemptionORM.jam_code_id == jam_code_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
