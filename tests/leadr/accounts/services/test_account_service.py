"""Tests for Account service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import AccountStatus
from leadr.accounts.services.account_service import AccountService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestAccountService:
    """Test suite for Account service."""

    async def test_create_account(self, db_session: AsyncSession):
        """Test creating an account via service."""
        service = AccountService(db_session)

        account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        assert account.id is not None
        assert account.name == "Acme Corporation"
        assert account.slug == "acme-corp"
        assert account.status == AccountStatus.ACTIVE

    async def test_get_account_by_id(self, db_session: AsyncSession):
        """Test retrieving an account by ID via service."""
        service = AccountService(db_session)

        # Create account
        created_account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Retrieve it
        account = await service.get_account(created_account.id)

        assert account is not None
        assert account.id == created_account.id
        assert account.name == "Acme Corporation"

    async def test_get_account_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent account returns None."""
        service = AccountService(db_session)
        non_existent_id = uuid4()

        account = await service.get_account(AccountID(non_existent_id))

        assert account is None

    async def test_get_account_by_slug(self, db_session: AsyncSession):
        """Test retrieving an account by slug via service."""
        service = AccountService(db_session)

        # Create account
        created_account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Retrieve by slug
        account = await service.get_account_by_slug("acme-corp")

        assert account is not None
        assert account.id == created_account.id
        assert account.slug == "acme-corp"

    async def test_get_account_by_slug_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent account by slug returns None."""
        service = AccountService(db_session)

        account = await service.get_account_by_slug("non-existent")

        assert account is None

    async def test_list_accounts(self, db_session: AsyncSession):
        """Test listing all accounts via service."""
        service = AccountService(db_session)

        # Create multiple accounts
        await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        await service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # List them
        accounts = await service.list_accounts()

        assert len(accounts) == 2
        slugs = {acc.slug for acc in accounts}
        assert "acme-corp" in slugs
        assert "beta-industries" in slugs

    async def test_suspend_account(self, db_session: AsyncSession):
        """Test suspending an account via service."""
        service = AccountService(db_session)

        # Create account
        created_account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Suspend it
        suspended_account = await service.suspend_account(created_account.id)

        assert suspended_account.status == AccountStatus.SUSPENDED

        # Verify in database
        account = await service.get_account(created_account.id)
        assert account is not None
        assert account.status == AccountStatus.SUSPENDED

    async def test_suspend_account_not_found(self, db_session: AsyncSession):
        """Test that suspending a non-existent account raises an error."""
        service = AccountService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.suspend_account(AccountID(non_existent_id))

        assert "Account not found" in str(exc_info.value)

    async def test_activate_account(self, db_session: AsyncSession):
        """Test activating an account via service."""
        service = AccountService(db_session)

        # Create and suspend account
        created_account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        await service.suspend_account(created_account.id)

        # Activate it
        activated_account = await service.activate_account(created_account.id)

        assert activated_account.status == AccountStatus.ACTIVE

        # Verify in database
        account = await service.get_account(created_account.id)
        assert account is not None
        assert account.status == AccountStatus.ACTIVE

    async def test_activate_account_not_found(self, db_session: AsyncSession):
        """Test that activating a non-existent account raises an error."""
        service = AccountService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.activate_account(AccountID(non_existent_id))

        assert "Account not found" in str(exc_info.value)

    async def test_delete_account(self, db_session: AsyncSession):
        """Test soft-deleting an account via service."""
        service = AccountService(db_session)

        # Create account
        created_account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Delete it
        await service.delete_account(created_account.id)

        # Verify it's not returned by normal queries
        account = await service.get_account(created_account.id)
        assert account is None

    async def test_delete_account_not_found(self, db_session: AsyncSession):
        """Test that deleting a non-existent account raises an error."""
        service = AccountService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.delete_account(AccountID(non_existent_id))

        assert "Account not found" in str(exc_info.value)

    async def test_list_accounts_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_accounts excludes soft-deleted accounts."""
        service = AccountService(db_session)

        # Create accounts
        account1 = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        await service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Delete one
        await service.delete_account(account1.id)

        # List should only return non-deleted
        accounts = await service.list_accounts()

        assert len(accounts) == 1
        assert accounts[0].slug == "beta-industries"
