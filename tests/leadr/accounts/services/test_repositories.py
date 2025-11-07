"""Tests for Account and User repository services."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestAccountRepository:
    """Test suite for Account repository."""

    async def test_create_account(self, db_session: AsyncSession):
        """Test creating an account via repository."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        created = await repo.create(account)

        assert created.id == account_id
        assert created.name == "Acme Corporation"
        assert created.slug == "acme-corp"
        assert created.status == AccountStatus.ACTIVE

    async def test_get_account_by_id(self, db_session: AsyncSession):
        """Test retrieving an account by ID."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Retrieve it
        retrieved = await repo.get_by_id(account_id)

        assert retrieved is not None
        assert retrieved.id == account_id
        assert retrieved.name == "Acme Corporation"

    async def test_get_account_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent account returns None."""
        repo = AccountRepository(db_session)
        non_existent_id = EntityID.generate()

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_account_by_slug(self, db_session: AsyncSession):
        """Test retrieving an account by slug."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Retrieve by slug
        retrieved = await repo.get_by_slug("acme-corp")

        assert retrieved is not None
        assert retrieved.id == account_id
        assert retrieved.slug == "acme-corp"

    async def test_update_account(self, db_session: AsyncSession):
        """Test updating an account via repository."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update it
        account.suspend()
        updated = await repo.update(account)

        assert updated.status == AccountStatus.SUSPENDED

        # Verify in database
        retrieved = await repo.get_by_id(account_id)
        assert retrieved is not None
        assert retrieved.status == AccountStatus.SUSPENDED

    async def test_delete_account(self, db_session: AsyncSession):
        """Test deleting an account via repository."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Delete it
        await repo.delete(account_id)

        # Verify it's gone
        retrieved = await repo.get_by_id(account_id)
        assert retrieved is None

    async def test_list_accounts(self, db_session: AsyncSession):
        """Test listing all accounts."""
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        # Create multiple accounts
        account1 = Account(
            id=EntityID.generate(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=EntityID.generate(),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        await repo.create(account1)
        await repo.create(account2)

        # List them
        accounts = await repo.list_all()

        assert len(accounts) == 2
        slugs = {acc.slug for acc in accounts}
        assert "acme-corp" in slugs
        assert "beta-industries" in slugs

    async def test_delete_account_is_soft_delete(self, db_session: AsyncSession):
        """Test that delete performs soft-delete, not hard-delete."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Soft-delete it
        await repo.delete(account_id)

        # Verify it's not returned by normal queries
        retrieved = await repo.get_by_id(account_id)
        assert retrieved is None

    async def test_list_accounts_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_all excludes soft-deleted accounts."""
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        # Create accounts
        account1 = Account(
            id=EntityID.generate(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=EntityID.generate(),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        await repo.create(account1)
        await repo.create(account2)

        # Soft-delete one
        await repo.delete(account1.id)

        # List should only return non-deleted
        accounts = await repo.list_all()

        assert len(accounts) == 1
        assert accounts[0].slug == "beta-industries"

    async def test_get_by_slug_excludes_deleted(self, db_session: AsyncSession):
        """Test that get_by_slug excludes soft-deleted accounts."""
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        # Create account
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Soft-delete it
        await repo.delete(account_id)

        # Should not be found by slug
        retrieved = await repo.get_by_slug("acme-corp")
        assert retrieved is None


@pytest.mark.asyncio
class TestUserRepository:
    """Test suite for User repository."""

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        created = await user_repo.create(user)

        assert created.id == user_id
        assert created.account_id == account_id
        assert created.email == "user@example.com"
        assert created.display_name == "John Doe"

    async def test_get_user_by_id(self, db_session: AsyncSession):
        """Test retrieving a user by ID."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Retrieve it
        retrieved = await user_repo.get_by_id(user_id)

        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "user@example.com"

    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test retrieving a user by email."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Retrieve by email
        retrieved = await user_repo.get_by_email("user@example.com")

        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "user@example.com"

    async def test_list_users_by_account(self, db_session: AsyncSession):
        """Test listing all users for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create multiple users
        user_repo = UserRepository(db_session)

        user1 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user1@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user2@example.com",
            display_name="Jane Smith",
            created_at=now,
            updated_at=now,
        )

        await user_repo.create(user1)
        await user_repo.create(user2)

        # List users for account
        users = await user_repo.list_by_account(account_id)

        assert len(users) == 2
        emails = {u.email for u in users}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_update_user(self, db_session: AsyncSession):
        """Test updating a user via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Update display name
        user.display_name = "John Smith"
        updated = await user_repo.update(user)

        assert updated.display_name == "John Smith"

        # Verify in database
        retrieved = await user_repo.get_by_id(user_id)
        assert retrieved is not None
        assert retrieved.display_name == "John Smith"

    async def test_delete_user(self, db_session: AsyncSession):
        """Test deleting a user via repository."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Delete it
        await user_repo.delete(user_id)

        # Verify it's gone
        retrieved = await user_repo.get_by_id(user_id)
        assert retrieved is None

    async def test_delete_user_is_soft_delete(self, db_session: AsyncSession):
        """Test that delete performs soft-delete, not hard-delete."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Soft-delete it
        await user_repo.delete(user_id)

        # Verify it's not returned by normal queries
        retrieved = await user_repo.get_by_id(user_id)
        assert retrieved is None

    async def test_list_users_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_by_account excludes soft-deleted users."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create users
        user_repo = UserRepository(db_session)

        user1 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user1@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user2@example.com",
            display_name="Jane Smith",
            created_at=now,
            updated_at=now,
        )

        await user_repo.create(user1)
        await user_repo.create(user2)

        # Soft-delete one
        await user_repo.delete(user1.id)

        # List should only return non-deleted
        users = await user_repo.list_by_account(account_id)

        assert len(users) == 1
        assert users[0].email == "user2@example.com"

    async def test_get_by_email_excludes_deleted(self, db_session: AsyncSession):
        """Test that get_by_email excludes soft-deleted users."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Soft-delete it
        await user_repo.delete(user_id)

        # Should not be found by email
        retrieved = await user_repo.get_by_email("user@example.com")
        assert retrieved is None
