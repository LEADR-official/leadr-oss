"""Tests for registration repositories."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID
from leadr.registration.adapters.orm import VerificationCodeStatusEnum
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption
from leadr.registration.domain.verification_code import VerificationCode, VerificationCodeStatus
from leadr.registration.services.repositories import (
    JamCodeRedemptionRepository,
    JamCodeRepository,
    VerificationCodeRepository,
)


@pytest.mark.asyncio
class TestVerificationCodeRepository:
    """Test VerificationCodeRepository."""

    async def test_create_verification_code(self, db_session: AsyncSession):
        """Test creating a verification code."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="test@example.com",
            code="ABC123",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        created = await repository.create(code)
        await db_session.commit()

        assert created.id == code.id
        assert created.email == "test@example.com"
        assert created.code == "ABC123"
        assert created.status == VerificationCodeStatus.PENDING

    async def test_get_by_id(self, db_session: AsyncSession):
        """Test retrieving verification code by ID."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="test@example.com",
            code="TEST01",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code)
        await db_session.commit()

        retrieved = await repository.get_by_id(code.id)
        assert retrieved is not None
        assert retrieved.id == code.id
        assert retrieved.email == "test@example.com"

    async def test_find_valid_code_by_email(self, db_session: AsyncSession):
        """Test finding valid code by email and code value."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="test@example.com",
            code="VALID1",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code)
        await db_session.commit()

        found = await repository.find_valid_code_by_email("test@example.com", "VALID1")
        assert found is not None
        assert found.id == code.id

    async def test_find_valid_code_case_insensitive(self, db_session: AsyncSession):
        """Test finding code is case insensitive."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="test@example.com",
            code="UPPER1",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code)
        await db_session.commit()

        # Search with lowercase should still find it
        found = await repository.find_valid_code_by_email("test@example.com", "upper1")
        assert found is not None
        assert found.id == code.id

    async def test_find_valid_code_not_found(self, db_session: AsyncSession):
        """Test finding non-existent code returns None."""
        repository = VerificationCodeRepository(db_session)

        found = await repository.find_valid_code_by_email("test@example.com", "NOEXIST")
        assert found is None

    async def test_find_valid_code_wrong_email(self, db_session: AsyncSession):
        """Test finding code with wrong email returns None."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="user1@example.com",
            code="CODE01",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code)
        await db_session.commit()

        found = await repository.find_valid_code_by_email("user2@example.com", "CODE01")
        assert found is None

    async def test_find_valid_code_excludes_used(self, db_session: AsyncSession):
        """Test that find_valid_code_by_email excludes used codes."""
        repository = VerificationCodeRepository(db_session)

        code = VerificationCode(
            email="test@example.com",
            code="USED01",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code)
        code.mark_as_used()
        await repository.update(code)
        await db_session.commit()

        found = await repository.find_valid_code_by_email("test@example.com", "USED01")
        assert found is None

    async def test_invalidate_codes_for_email(self, db_session: AsyncSession):
        """Test invalidating all pending codes for an email."""
        repository = VerificationCodeRepository(db_session)

        # Create multiple pending codes
        code1 = VerificationCode(
            email="test@example.com",
            code="CODE01",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        code2 = VerificationCode(
            email="test@example.com",
            code="CODE02",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        code3 = VerificationCode(
            email="other@example.com",
            code="CODE03",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code1)
        await repository.create(code2)
        await repository.create(code3)
        await db_session.commit()

        # Invalidate codes for test@example.com
        await repository.invalidate_codes_for_email("test@example.com")
        await db_session.commit()

        # Codes for test@example.com should now be expired
        found1 = await repository.find_valid_code_by_email("test@example.com", "CODE01")
        found2 = await repository.find_valid_code_by_email("test@example.com", "CODE02")
        assert found1 is None
        assert found2 is None

        # Code for other@example.com should still be valid
        found3 = await repository.find_valid_code_by_email("other@example.com", "CODE03")
        assert found3 is not None

    async def test_filter_by_email(self, db_session: AsyncSession):
        """Test filtering verification codes by email."""
        repository = VerificationCodeRepository(db_session)

        code1 = VerificationCode(
            email="user1@example.com",
            code="CODE11",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        code2 = VerificationCode(
            email="user2@example.com",
            code="CODE22",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        code3 = VerificationCode(
            email="user1@example.com",
            code="CODE33",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code1)
        await repository.create(code2)
        await repository.create(code3)
        await db_session.commit()

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(email="user1@example.com", pagination=pagination)
        assert len(result.items) == 2
        assert all(r.email == "user1@example.com" for r in result.items)

    async def test_filter_by_status(self, db_session: AsyncSession):
        """Test filtering verification codes by status."""
        repository = VerificationCodeRepository(db_session)

        code1 = VerificationCode(
            email="test@example.com",
            code="CODE55",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        code2 = VerificationCode(
            email="test@example.com",
            code="CODE66",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        await repository.create(code1)
        await repository.create(code2)
        code2.mark_as_used()
        await repository.update(code2)
        await db_session.commit()

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        pending = await repository.filter(
            status=VerificationCodeStatusEnum.PENDING, pagination=pagination
        )
        used = await repository.filter(
            status=VerificationCodeStatusEnum.USED, pagination=pagination
        )

        assert len(pending.items) == 1
        assert len(used.items) == 1


@pytest.mark.asyncio
class TestJamCodeRepository:
    """Test JamCodeRepository."""

    async def test_create_jam_code(self, db_session: AsyncSession):
        """Test creating a jam code."""
        repository = JamCodeRepository(db_session)

        jam_code = JamCode(
            code="SUMMER2024",
            description="Summer promotion",
            features={"discount": 20},
            max_uses=100,
        )

        created = await repository.create(jam_code)
        await db_session.commit()

        assert created.id == jam_code.id
        assert created.code == "SUMMER2024"
        assert created.description == "Summer promotion"

    async def test_get_by_id(self, db_session: AsyncSession):
        """Test retrieving jam code by ID."""
        repository = JamCodeRepository(db_session)

        jam_code = JamCode(
            code="TEST123",
            description="Test code",
            features={},
        )

        await repository.create(jam_code)
        await db_session.commit()

        retrieved = await repository.get_by_id(jam_code.id)
        assert retrieved is not None
        assert retrieved.id == jam_code.id

    async def test_find_by_code(self, db_session: AsyncSession):
        """Test finding jam code by code value."""
        repository = JamCodeRepository(db_session)

        jam_code = JamCode(
            code="FINDME",
            description="Find this code",
            features={},
        )

        await repository.create(jam_code)
        await db_session.commit()

        found = await repository.find_by_code("FINDME")
        assert found is not None
        assert found.id == jam_code.id

    async def test_find_by_code_case_insensitive(self, db_session: AsyncSession):
        """Test finding jam code is case insensitive."""
        repository = JamCodeRepository(db_session)

        jam_code = JamCode(
            code="UPPER",
            description="Test",
            features={},
        )

        await repository.create(jam_code)
        await db_session.commit()

        # Search with lowercase
        found = await repository.find_by_code("upper")
        assert found is not None
        assert found.id == jam_code.id

    async def test_find_by_code_not_found(self, db_session: AsyncSession):
        """Test finding non-existent jam code returns None."""
        repository = JamCodeRepository(db_session)

        found = await repository.find_by_code("NOEXIST")
        assert found is None

    async def test_update_jam_code(self, db_session: AsyncSession):
        """Test updating a jam code."""
        repository = JamCodeRepository(db_session)

        jam_code = JamCode(
            code="UPDATE",
            description="Original",
            features={},
        )

        await repository.create(jam_code)
        await db_session.commit()

        jam_code.description = "Updated"
        jam_code.deactivate()
        updated = await repository.update(jam_code)
        await db_session.commit()

        assert updated.description == "Updated"
        assert updated.active is False

    async def test_filter_by_code(self, db_session: AsyncSession):
        """Test filtering jam codes by code value."""
        repository = JamCodeRepository(db_session)

        code1 = JamCode(code="CODE1", description="Test 1", features={})
        code2 = JamCode(code="CODE2", description="Test 2", features={})

        await repository.create(code1)
        await repository.create(code2)
        await db_session.commit()

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(code="CODE1", pagination=pagination)
        assert len(result.items) == 1
        assert result.items[0].code == "CODE1"


@pytest.mark.asyncio
class TestJamCodeRedemptionRepository:
    """Test JamCodeRedemptionRepository."""

    async def test_create_redemption(self, db_session: AsyncSession, test_account):
        """Test creating a jam code redemption."""
        # First create a jam code
        jam_code_repo = JamCodeRepository(db_session)
        jam_code = JamCode(code="REDEEM1", description="Test", features={})
        await jam_code_repo.create(jam_code)
        await db_session.commit()

        # Create redemption
        repository = JamCodeRedemptionRepository(db_session)

        redemption = JamCodeRedemption(
            jam_code_id=jam_code.id,
            account_id=test_account.id,
            meta={"source": "web"},
        )

        created = await repository.create(redemption)
        await db_session.commit()

        assert created.id == redemption.id
        assert created.jam_code_id == jam_code.id
        assert created.account_id == test_account.id

    async def test_get_by_id(self, db_session: AsyncSession, test_account):
        """Test retrieving redemption by ID."""
        jam_code_repo = JamCodeRepository(db_session)
        jam_code = JamCode(code="GET1", description="Test", features={})
        await jam_code_repo.create(jam_code)

        repository = JamCodeRedemptionRepository(db_session)

        redemption = JamCodeRedemption(
            jam_code_id=jam_code.id,
            account_id=test_account.id,
            meta={},
        )

        await repository.create(redemption)
        await db_session.commit()

        retrieved = await repository.get_by_id(redemption.id)
        assert retrieved is not None
        assert retrieved.id == redemption.id

    async def test_find_by_account(self, db_session: AsyncSession, test_account):
        """Test finding redemptions by account ID."""
        # Create a second test account for comparison

        account_repo = AccountRepository(db_session)
        account2_id = AccountID()
        now = datetime.now(UTC)
        account2 = Account(
            id=account2_id,
            name="Test Account 2",
            slug=f"test2-{str(account2_id.uuid)[:8]}",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account2)

        jam_code_repo = JamCodeRepository(db_session)
        code1 = JamCode(code="FIND1", description="Test 1", features={})
        code2 = JamCode(code="FIND2", description="Test 2", features={})
        await jam_code_repo.create(code1)
        await jam_code_repo.create(code2)

        repository = JamCodeRedemptionRepository(db_session)

        # Account 1 redeems both codes
        redemption1 = JamCodeRedemption(jam_code_id=code1.id, account_id=test_account.id, meta={})
        redemption2 = JamCodeRedemption(jam_code_id=code2.id, account_id=test_account.id, meta={})
        # Account 2 redeems code1
        redemption3 = JamCodeRedemption(jam_code_id=code1.id, account_id=account2.id, meta={})

        await repository.create(redemption1)
        await repository.create(redemption2)
        await repository.create(redemption3)
        await db_session.commit()

        # Find redemptions for account 1
        results = await repository.find_by_account(test_account.id)
        assert len(results) == 2
        assert all(r.account_id == test_account.id for r in results)

    async def test_has_redeemed_true(self, db_session: AsyncSession, test_account):
        """Test has_redeemed returns True when account redeemed code."""
        jam_code_repo = JamCodeRepository(db_session)
        jam_code = JamCode(code="CHECK1", description="Test", features={})
        await jam_code_repo.create(jam_code)

        repository = JamCodeRedemptionRepository(db_session)

        redemption = JamCodeRedemption(jam_code_id=jam_code.id, account_id=test_account.id, meta={})

        await repository.create(redemption)
        await db_session.commit()

        has_redeemed = await repository.has_redeemed(test_account.id, jam_code.id)
        assert has_redeemed is True

    async def test_has_redeemed_false(self, db_session: AsyncSession, test_account):
        """Test has_redeemed returns False when account hasn't redeemed."""
        jam_code_repo = JamCodeRepository(db_session)
        jam_code = JamCode(code="CHECK2", description="Test", features={})
        await jam_code_repo.create(jam_code)

        repository = JamCodeRedemptionRepository(db_session)

        has_redeemed = await repository.has_redeemed(test_account.id, jam_code.id)
        assert has_redeemed is False

    async def test_filter_by_account_id(self, db_session: AsyncSession, test_account):
        """Test filtering redemptions by account ID."""
        # Create a second test account for comparison

        account_repo = AccountRepository(db_session)
        account2_id = AccountID()
        now = datetime.now(UTC)
        account2 = Account(
            id=account2_id,
            name="Test Account 3",
            slug=f"test3-{str(account2_id.uuid)[:8]}",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account2)

        jam_code_repo = JamCodeRepository(db_session)
        jam_code = JamCode(code="FILTER1", description="Test", features={})
        await jam_code_repo.create(jam_code)

        repository = JamCodeRedemptionRepository(db_session)

        redemption1 = JamCodeRedemption(
            jam_code_id=jam_code.id, account_id=test_account.id, meta={}
        )
        redemption2 = JamCodeRedemption(jam_code_id=jam_code.id, account_id=account2.id, meta={})

        await repository.create(redemption1)
        await repository.create(redemption2)
        await db_session.commit()

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(account_id=test_account.id.uuid, pagination=pagination)
        assert len(result.items) == 1
        assert result.items[0].account_id == test_account.id
