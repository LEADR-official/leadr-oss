"""Tests for User service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, UserID


@pytest.mark.asyncio
class TestUserService:
    """Test suite for User service."""

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        # Create user
        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        assert user.account_id == account_id
        assert user.email == "user@example.com"
        assert user.display_name == "John Doe"
        assert user.id is not None

    async def test_get_user_by_id(self, db_session: AsyncSession):
        """Test retrieving a user by ID."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Retrieve it
        retrieved = await service.get_user(user.id)

        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "user@example.com"

    async def test_get_user_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent user returns None."""
        service = UserService(db_session)
        non_existent_id = uuid4()

        result = await service.get_user(UserID(non_existent_id))

        assert result is None

    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test retrieving a user by email."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Retrieve by email
        retrieved = await service.get_user_by_email("user@example.com")

        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "user@example.com"

    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent user by email returns None."""
        service = UserService(db_session)

        result = await service.get_user_by_email("nonexistent@example.com")

        assert result is None

    async def test_list_users_by_account(self, db_session: AsyncSession):
        """Test listing all users for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        # Create multiple users
        service = UserService(db_session)
        await service.create_user(
            account_id=account_id,
            email="user1@example.com",
            display_name="User One",
        )
        await service.create_user(
            account_id=account_id,
            email="user2@example.com",
            display_name="User Two",
        )

        # List them
        users = await service.list_users_by_account(account_id)

        assert len(users) == 2
        emails = {u.email for u in users}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_list_users_excludes_deleted(self, db_session: AsyncSession):
        """Test that listing users excludes soft-deleted users."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        # Create users
        service = UserService(db_session)
        user1 = await service.create_user(
            account_id=account_id,
            email="user1@example.com",
            display_name="User One",
        )
        await service.create_user(
            account_id=account_id,
            email="user2@example.com",
            display_name="User Two",
        )

        # Delete one
        await service.delete_user(user1.id)

        # List should only return non-deleted
        users = await service.list_users_by_account(account_id)

        assert len(users) == 1
        assert users[0].email == "user2@example.com"

    async def test_update_user(self, db_session: AsyncSession):
        """Test updating a user."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Update email and display name
        updated = await service.update_user(
            user_id=user.id,
            email="newemail@example.com",
            display_name="Jane Smith",
        )

        assert updated.email == "newemail@example.com"
        assert updated.display_name == "Jane Smith"

        # Verify in database
        retrieved = await service.get_user(user.id)
        assert retrieved is not None
        assert retrieved.email == "newemail@example.com"
        assert retrieved.display_name == "Jane Smith"

    async def test_update_user_partial_email(self, db_session: AsyncSession):
        """Test updating only the email of a user."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Update only email
        updated = await service.update_user(
            user_id=user.id,
            email="newemail@example.com",
        )

        assert updated.email == "newemail@example.com"
        assert updated.display_name == "John Doe"  # unchanged

    async def test_update_user_partial_display_name(self, db_session: AsyncSession):
        """Test updating only the display name of a user."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Update only display name
        updated = await service.update_user(
            user_id=user.id,
            display_name="Jane Smith",
        )

        assert updated.email == "user@example.com"  # unchanged
        assert updated.display_name == "Jane Smith"

    async def test_update_user_not_found(self, db_session: AsyncSession):
        """Test that updating a non-existent user raises EntityNotFoundError."""
        service = UserService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.update_user(
                user_id=UserID(non_existent_id),
                email="newemail@example.com",
            )

        assert "User not found" in str(exc_info.value)

    async def test_delete_user(self, db_session: AsyncSession):
        """Test soft-deleting a user."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Delete it
        await service.delete_user(user.id)

        # Should not be found
        retrieved = await service.get_user(user.id)
        assert retrieved is None

    async def test_delete_user_not_found(self, db_session: AsyncSession):
        """Test that deleting a non-existent user raises EntityNotFoundError."""
        service = UserService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.delete_user(UserID(non_existent_id))

        assert "User not found" in str(exc_info.value)

    async def test_create_superadmin_user(self, db_session: AsyncSession):
        """Test creating a user with superadmin privileges."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="LEADR",
            slug="leadr",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        # Create superadmin user
        service = UserService(db_session)
        user = await service.create_user(
            account_id=account_id,
            email="admin@leadr.gg",
            display_name="LEADR Admin",
            super_admin=True,
        )

        assert user.account_id == account_id
        assert user.email == "admin@leadr.gg"
        assert user.super_admin is True

    async def test_find_superadmins(self, db_session: AsyncSession):
        """Test finding all superadmin users."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="LEADR",
            slug="leadr",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)

        # Create regular user
        await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
        )

        # Create superadmin users
        superadmin1 = await service.create_user(
            account_id=account_id,
            email="admin1@leadr.gg",
            display_name="Admin 1",
            super_admin=True,
        )

        superadmin2 = await service.create_user(
            account_id=account_id,
            email="admin2@leadr.gg",
            display_name="Admin 2",
            super_admin=True,
        )

        # Find all superadmins
        superadmins = await service.find_superadmins()

        assert len(superadmins) == 2
        superadmin_ids = {sa.id for sa in superadmins}
        assert superadmin1.id in superadmin_ids
        assert superadmin2.id in superadmin_ids

    async def test_superadmin_exists_true(self, db_session: AsyncSession):
        """Test that superadmin_exists returns True when superadmin exists."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="LEADR",
            slug="leadr",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)

        # Create superadmin
        await service.create_user(
            account_id=account_id,
            email="admin@leadr.gg",
            display_name="LEADR Admin",
            super_admin=True,
        )

        # Check if superadmin exists
        exists = await service.superadmin_exists()
        assert exists is True

    async def test_superadmin_exists_false(self, db_session: AsyncSession):
        """Test that superadmin_exists returns False when no superadmin exists."""
        service = UserService(db_session)

        # Check if superadmin exists (should be False)
        exists = await service.superadmin_exists()
        assert exists is False

    async def test_find_superadmins_excludes_deleted(self, db_session: AsyncSession):
        """Test that find_superadmins excludes soft-deleted users."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())

        account = Account(
            id=account_id,
            name="LEADR",
            slug="leadr",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        service = UserService(db_session)

        # Create superadmin
        superadmin = await service.create_user(
            account_id=account_id,
            email="admin@leadr.gg",
            display_name="LEADR Admin",
            super_admin=True,
        )

        # Delete the superadmin
        await service.delete_user(superadmin.id)

        # Find superadmins (should be empty)
        superadmins = await service.find_superadmins()
        assert len(superadmins) == 0

        # superadmin_exists should return False
        exists = await service.superadmin_exists()
        assert exists is False
