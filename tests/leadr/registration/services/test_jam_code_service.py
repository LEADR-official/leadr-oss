"""Tests for jam code service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID
from leadr.registration.services.jam_code_service import JamCodeService


@pytest.mark.asyncio
class TestJamCodeServiceValidateAndGet:
    """Test JamCodeService.validate_and_get_jam_code method."""

    async def test_validate_valid_code(self, db_session: AsyncSession):
        """Test validating a valid jam code."""
        service = JamCodeService(db_session)

        # Create a valid jam code
        jam_code = await service.create_jam_code(
            code="VALID2024",
            description="Valid code",
            features={"premium": True},
        )

        # Validate it
        validated = await service.validate_and_get_jam_code("VALID2024")

        assert validated is not None
        assert validated.id == jam_code.id
        assert validated.code == "VALID2024"

    async def test_validate_nonexistent_code(self, db_session: AsyncSession):
        """Test validating a non-existent code returns None."""
        service = JamCodeService(db_session)

        validated = await service.validate_and_get_jam_code("NOEXIST")
        assert validated is None

    async def test_validate_inactive_code(self, db_session: AsyncSession):
        """Test validating an inactive code returns None."""
        service = JamCodeService(db_session)

        # Create and deactivate a code
        jam_code = await service.create_jam_code(
            code="INACTIVE",
            description="Inactive code",
            features={},
        )

        jam_code.deactivate()
        await service.jam_code_repository.update(jam_code)
        await db_session.commit()

        validated = await service.validate_and_get_jam_code("INACTIVE")
        assert validated is None

    async def test_validate_expired_code(self, db_session: AsyncSession):
        """Test validating an expired code returns None."""
        service = JamCodeService(db_session)

        # Create a code that expired yesterday
        past_date = datetime.now(UTC) - timedelta(days=1)
        await service.create_jam_code(
            code="EXPIRED",
            description="Expired code",
            features={},
            expires_at=past_date,
        )

        validated = await service.validate_and_get_jam_code("EXPIRED")
        assert validated is None

    async def test_validate_max_uses_reached(self, db_session: AsyncSession):
        """Test validating a code that reached max uses returns None."""
        service = JamCodeService(db_session)

        # Create a code with max_uses=1
        jam_code = await service.create_jam_code(
            code="MAXED",
            description="Maxed code",
            features={},
            max_uses=1,
        )

        # Use it once
        jam_code.increment_uses()
        await service.jam_code_repository.update(jam_code)
        await db_session.commit()

        validated = await service.validate_and_get_jam_code("MAXED")
        assert validated is None

    async def test_validate_case_insensitive(self, db_session: AsyncSession):
        """Test validation is case insensitive."""
        service = JamCodeService(db_session)

        await service.create_jam_code(
            code="UPPER",
            description="Test",
            features={},
        )

        validated = await service.validate_and_get_jam_code("upper")
        assert validated is not None
        assert validated.code == "UPPER"


@pytest.mark.asyncio
class TestJamCodeServiceRedemption:
    """Test JamCodeService.redeem_jam_code method."""

    async def test_redeem_jam_code_success(self, db_session: AsyncSession, test_account):
        """Test successful jam code redemption."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="REDEEM1",
            description="Test",
            features={"premium": True},
        )

        redemption = await service.redeem_jam_code(
            jam_code=jam_code,
            account_id=test_account.id,
            meta={"source": "web"},
        )

        assert redemption.jam_code_id == jam_code.id
        assert redemption.account_id == test_account.id
        assert redemption.meta == {"source": "web"}

        # Verify uses incremented
        updated_code = await service.get_jam_code_by_id(jam_code.id)
        assert updated_code is not None
        assert updated_code.current_uses == 1

    async def test_redeem_jam_code_increments_uses(self, db_session: AsyncSession, test_account):
        """Test that redemption increments use count."""

        service = JamCodeService(db_session)
        account_repo = AccountRepository(db_session)

        # Create a second account
        account2 = Account(
            id=AccountID(),
            name="Test Account 2",
            slug="test-account-2",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account2)
        await db_session.commit()

        jam_code = await service.create_jam_code(
            code="MULTI",
            description="Multi-use code",
            features={},
            max_uses=10,
        )

        # Redeem twice with different accounts
        await service.redeem_jam_code(jam_code, test_account.id)
        await service.redeem_jam_code(jam_code, account2.id)

        updated_code = await service.get_jam_code_by_id(jam_code.id)
        assert updated_code is not None
        assert updated_code.current_uses == 2

    async def test_redeem_duplicate_raises_error(self, db_session: AsyncSession, test_account):
        """Test that redeeming same code twice for same account raises error."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="ONCE",
            description="One per account",
            features={},
        )

        # Redeem once
        await service.redeem_jam_code(jam_code, test_account.id)

        # Try to redeem again
        with pytest.raises(ValueError, match="already redeemed this jam code"):
            await service.redeem_jam_code(jam_code, test_account.id)

    async def test_redeem_with_meta(self, db_session: AsyncSession, test_account):
        """Test redeeming with metadata."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="META",
            description="Test",
            features={"feature": "value"},
        )

        meta = {"referrer": "friend", "campaign": "summer"}
        redemption = await service.redeem_jam_code(jam_code, test_account.id, meta)

        assert redemption.meta == meta

    async def test_redeem_with_none_meta(self, db_session: AsyncSession, test_account):
        """Test redeeming without metadata uses empty dict."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="NOMETA",
            description="Test",
            features={},
        )

        redemption = await service.redeem_jam_code(jam_code, test_account.id, meta=None)

        assert redemption.meta == {}


@pytest.mark.asyncio
class TestJamCodeServiceCreate:
    """Test JamCodeService.create_jam_code method."""

    async def test_create_minimal(self, db_session: AsyncSession):
        """Test creating jam code with minimal fields."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="MINIMAL",
            description="Minimal code",
        )

        assert jam_code.code == "MINIMAL"
        assert jam_code.description == "Minimal code"
        assert jam_code.features == {}
        assert jam_code.max_uses is None
        assert jam_code.expires_at is None
        assert jam_code.active is True
        assert jam_code.current_uses == 0

    async def test_create_with_all_fields(self, db_session: AsyncSession):
        """Test creating jam code with all fields."""
        service = JamCodeService(db_session)
        expires_at = datetime.now(UTC) + timedelta(days=30)

        jam_code = await service.create_jam_code(
            code="FULL",
            description="Full featured code",
            features={"premium": True, "discount": 20},
            max_uses=100,
            expires_at=expires_at,
        )

        assert jam_code.code == "FULL"
        assert jam_code.description == "Full featured code"
        assert jam_code.features == {"premium": True, "discount": 20}
        assert jam_code.max_uses == 100
        assert jam_code.expires_at == expires_at

    async def test_create_normalizes_code_to_uppercase(self, db_session: AsyncSession):
        """Test that code is normalized to uppercase."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="lowercase",
            description="Test",
        )

        assert jam_code.code == "LOWERCASE"

    async def test_create_duplicate_raises_error(self, db_session: AsyncSession):
        """Test creating duplicate code raises error."""
        service = JamCodeService(db_session)

        await service.create_jam_code(code="DUPLICATE", description="First")

        with pytest.raises(ValueError, match="already exists"):
            await service.create_jam_code(code="DUPLICATE", description="Second")

    async def test_create_duplicate_case_insensitive(self, db_session: AsyncSession):
        """Test duplicate check is case insensitive."""
        service = JamCodeService(db_session)

        await service.create_jam_code(code="CASE", description="First")

        with pytest.raises(ValueError, match="already exists"):
            await service.create_jam_code(code="case", description="Second")


@pytest.mark.asyncio
class TestJamCodeServiceGet:
    """Test JamCodeService.get_jam_code_by_id method."""

    async def test_get_by_id_exists(self, db_session: AsyncSession):
        """Test getting jam code by ID."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="GETME", description="Test")

        retrieved = await service.get_jam_code_by_id(jam_code.id)

        assert retrieved is not None
        assert retrieved.id == jam_code.id

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent jam code returns None."""

        service = JamCodeService(db_session)

        retrieved = await service.get_jam_code_by_id(uuid4())
        assert retrieved is None


@pytest.mark.asyncio
class TestJamCodeServiceList:
    """Test JamCodeService.list_jam_codes method."""

    async def test_list_empty(self, db_session: AsyncSession):
        """Test listing when no codes exist."""
        service = JamCodeService(db_session)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_jam_codes(pagination=pagination)
        assert result.items == []

    async def test_list_multiple_codes(self, db_session: AsyncSession):
        """Test listing multiple jam codes."""
        service = JamCodeService(db_session)

        await service.create_jam_code(code="CODE1", description="First")
        await service.create_jam_code(code="CODE2", description="Second")
        await service.create_jam_code(code="CODE3", description="Third")

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_jam_codes(pagination=pagination)
        assert len(result.items) == 3


@pytest.mark.asyncio
class TestJamCodeServiceUpdate:
    """Test JamCodeService.update_jam_code method."""

    async def test_update_description(self, db_session: AsyncSession):
        """Test updating description."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE1", description="Original")

        updated = await service.update_jam_code(
            jam_code_id=jam_code.id,
            description="Updated description",
        )

        assert updated.description == "Updated description"

    async def test_update_features(self, db_session: AsyncSession):
        """Test updating features."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="UPDATE2", description="Test", features={"old": True}
        )

        updated = await service.update_jam_code(
            jam_code_id=jam_code.id,
            features={"new": True},
        )

        assert updated.features == {"new": True}

    async def test_update_max_uses(self, db_session: AsyncSession):
        """Test updating max uses."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE3", description="Test", max_uses=10)

        updated = await service.update_jam_code(jam_code_id=jam_code.id, max_uses=20)

        assert updated.max_uses == 20

    async def test_update_active_to_false(self, db_session: AsyncSession):
        """Test deactivating jam code."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE4", description="Test")

        updated = await service.update_jam_code(jam_code_id=jam_code.id, active=False)

        assert updated.active is False

    async def test_update_active_to_true(self, db_session: AsyncSession):
        """Test activating jam code."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE5", description="Test")
        jam_code.deactivate()
        await service.jam_code_repository.update(jam_code)
        await db_session.commit()

        updated = await service.update_jam_code(jam_code_id=jam_code.id, active=True)

        assert updated.active is True

    async def test_update_expires_at(self, db_session: AsyncSession):
        """Test updating expiration date."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE6", description="Test")

        new_expiry = datetime.now(UTC) + timedelta(days=60)
        updated = await service.update_jam_code(
            jam_code_id=jam_code.id,
            expires_at=new_expiry,
        )

        assert updated.expires_at == new_expiry

    async def test_update_multiple_fields(self, db_session: AsyncSession):
        """Test updating multiple fields at once."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(code="UPDATE7", description="Original")

        updated = await service.update_jam_code(
            jam_code_id=jam_code.id,
            description="New description",
            features={"updated": True},
            max_uses=50,
            active=False,
        )

        assert updated.description == "New description"
        assert updated.features == {"updated": True}
        assert updated.max_uses == 50
        assert updated.active is False

    async def test_update_nonexistent_raises_error(self, db_session: AsyncSession):
        """Test updating non-existent jam code raises error."""

        service = JamCodeService(db_session)

        with pytest.raises(ValueError, match="Jam code not found"):
            await service.update_jam_code(
                jam_code_id=uuid4(),
                description="Won't work",
            )

    async def test_update_with_none_values_ignored(self, db_session: AsyncSession):
        """Test that None values don't update fields."""
        service = JamCodeService(db_session)

        jam_code = await service.create_jam_code(
            code="UPDATE8",
            description="Original",
            features={"keep": True},
            max_uses=10,
        )

        # Update with all None values
        updated = await service.update_jam_code(
            jam_code_id=jam_code.id,
            description=None,
            features=None,
            max_uses=None,
            active=None,
            expires_at=None,
        )

        # Nothing should change
        assert updated.description == "Original"
        assert updated.features == {"keep": True}
        assert updated.max_uses == 10
