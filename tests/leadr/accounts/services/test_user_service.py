"""Tests for User service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.accounts.domain.user import User, UserStatus
from leadr.accounts.services.user_service import UserService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.mark.asyncio
class TestUserService:
    """Test suite for User service."""

    @pytest.fixture
    def service(self, mock_session):
        """Create UserService with mock repository."""
        mock_repo = MagicMock()
        return UserService(mock_session, repository=mock_repo)

    async def test_create_user(self, service):
        """Test creating a user."""
        account_id = AccountID(uuid4())

        # Mock repository.create to return the user
        async def mock_create(user):
            return user

        service.repository.create = AsyncMock(side_effect=mock_create)

        # Create user
        user = await service.create_user(
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        assert user.account_id == account_id
        assert user.email == "user@example.com"
        assert user.display_name == "John Doe"
        assert user.id is not None
        service.repository.create.assert_awaited_once()

    async def test_get_user_by_id(self, service):
        """Test retrieving a user by ID."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Retrieve it
        retrieved = await service.get_user(user_id)

        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "user@example.com"
        service.repository.get_by_id.assert_awaited_once_with(user_id.uuid)

    async def test_get_user_not_found(self, service):
        """Test retrieving a non-existent user returns None."""
        non_existent_id = UserID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_user(non_existent_id)

        assert result is None
        service.repository.get_by_id.assert_awaited_once_with(non_existent_id.uuid)

    async def test_get_user_by_email(self, service):
        """Test retrieving a user by email."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_email
        service.repository.get_by_email = AsyncMock(return_value=mock_user)

        # Retrieve by email
        retrieved = await service.get_user_by_email("user@example.com")

        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "user@example.com"
        service.repository.get_by_email.assert_awaited_once_with("user@example.com")

    async def test_get_user_by_email_not_found(self, service):
        """Test retrieving a non-existent user by email returns None."""
        # Mock repository.get_by_email to return None
        service.repository.get_by_email = AsyncMock(return_value=None)

        result = await service.get_user_by_email("nonexistent@example.com")

        assert result is None
        service.repository.get_by_email.assert_awaited_once_with("nonexistent@example.com")

    async def test_list_users_by_account(self, service):
        """Test listing all users for an account."""
        account_id = AccountID(uuid4())

        # Mock users
        user1 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="user1@example.com",
            display_name="User One",
        )
        user2 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="user2@example.com",
            display_name="User Two",
        )

        # Mock paginated result
        mock_result = PaginatedResult(
            items=[user1, user2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Mock repository.filter
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List them
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_users_by_account(account_id, pagination=pagination)

        assert len(result.items) == 2
        emails = {u.email for u in result.items}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails
        service.repository.filter.assert_awaited_once_with(account_id, pagination=pagination)

    async def test_list_users_excludes_deleted(self, service):
        """Test that listing users excludes soft-deleted users."""
        account_id = AccountID(uuid4())

        # Mock only one user (deleted one excluded by repository)
        user2 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="user2@example.com",
            display_name="User Two",
        )

        # Mock paginated result with only non-deleted user
        mock_result = PaginatedResult(
            items=[user2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Mock repository.filter to return only non-deleted
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List should only return non-deleted
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_users_by_account(account_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].email == "user2@example.com"

    async def test_update_user(self, service):
        """Test updating a user."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.update to return updated user
        async def mock_update(user):
            return user

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Update email and display name
        updated = await service.update_user(
            user_id=user_id,
            email="newemail@example.com",
            display_name="Jane Smith",
        )

        assert updated.email == "newemail@example.com"
        assert updated.display_name == "Jane Smith"
        service.repository.get_by_id.assert_awaited_once_with(user_id.uuid)
        service.repository.update.assert_awaited_once()

    async def test_update_user_partial_email(self, service):
        """Test updating only the email of a user."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.update to return updated user
        async def mock_update(user):
            return user

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Update only email
        updated = await service.update_user(
            user_id=user_id,
            email="newemail@example.com",
        )

        assert updated.email == "newemail@example.com"
        assert updated.display_name == "John Doe"  # unchanged

    async def test_update_user_partial_display_name(self, service):
        """Test updating only the display name of a user."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.update to return updated user
        async def mock_update(user):
            return user

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Update only display name
        updated = await service.update_user(
            user_id=user_id,
            display_name="Jane Smith",
        )

        assert updated.email == "user@example.com"  # unchanged
        assert updated.display_name == "Jane Smith"

    async def test_update_user_not_found(self, service):
        """Test that updating a non-existent user raises EntityNotFoundError."""
        non_existent_id = UserID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.update_user(
                user_id=non_existent_id,
                email="newemail@example.com",
            )

        assert "User not found" in str(exc_info.value)
        service.repository.get_by_id.assert_awaited_once_with(non_existent_id.uuid)

    async def test_delete_user(self, service):
        """Test soft-deleting a user."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.delete
        service.repository.delete = AsyncMock()

        # Delete it
        await service.delete_user(user_id)

        service.repository.get_by_id.assert_awaited_once_with(user_id.uuid)
        service.repository.delete.assert_awaited_once_with(user_id.uuid)

    async def test_delete_user_not_found(self, service):
        """Test that deleting a non-existent user raises EntityNotFoundError."""
        non_existent_id = UserID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.delete_user(non_existent_id)

        assert "User not found" in str(exc_info.value)
        service.repository.get_by_id.assert_awaited_once_with(non_existent_id.uuid)

    async def test_create_superadmin_user(self, service):
        """Test creating a user with superadmin privileges."""
        account_id = AccountID(uuid4())

        # Mock repository.create to return the user
        async def mock_create(user):
            return user

        service.repository.create = AsyncMock(side_effect=mock_create)

        # Create superadmin user
        user = await service.create_user(
            account_id=account_id,
            email="admin@leadr.gg",
            display_name="LEADR Admin",
            super_admin=True,
        )

        assert user.account_id == account_id
        assert user.email == "admin@leadr.gg"
        assert user.super_admin is True
        service.repository.create.assert_awaited_once()

    async def test_find_superadmins(self, service):
        """Test finding all superadmin users."""
        account_id = AccountID(uuid4())

        # Create superadmin users
        superadmin1 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="admin1@leadr.gg",
            display_name="Admin 1",
            super_admin=True,
        )

        superadmin2 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="admin2@leadr.gg",
            display_name="Admin 2",
            super_admin=True,
        )

        # Mock repository.find_superadmins
        service.repository.find_superadmins = AsyncMock(return_value=[superadmin1, superadmin2])

        # Find all superadmins
        superadmins = await service.find_superadmins()

        assert len(superadmins) == 2
        superadmin_ids = {sa.id for sa in superadmins}
        assert superadmin1.id in superadmin_ids
        assert superadmin2.id in superadmin_ids
        service.repository.find_superadmins.assert_awaited_once()

    async def test_superadmin_exists_true(self, service):
        """Test that superadmin_exists returns True when superadmin exists."""
        account_id = AccountID(uuid4())

        # Create superadmin
        superadmin = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="admin@leadr.gg",
            display_name="LEADR Admin",
            super_admin=True,
        )

        # Mock repository.find_superadmins
        service.repository.find_superadmins = AsyncMock(return_value=[superadmin])

        # Check if superadmin exists
        exists = await service.superadmin_exists()
        assert exists is True
        service.repository.find_superadmins.assert_awaited_once()

    async def test_superadmin_exists_false(self, service):
        """Test that superadmin_exists returns False when no superadmin exists."""
        # Mock repository.find_superadmins to return empty list
        service.repository.find_superadmins = AsyncMock(return_value=[])

        # Check if superadmin exists (should be False)
        exists = await service.superadmin_exists()
        assert exists is False
        service.repository.find_superadmins.assert_awaited_once()

    async def test_find_superadmins_excludes_deleted(self, service):
        """Test that find_superadmins excludes soft-deleted users."""
        # Mock repository.find_superadmins to return empty list (deleted excluded by repository)
        service.repository.find_superadmins = AsyncMock(return_value=[])

        # Find superadmins (should be empty)
        superadmins = await service.find_superadmins()
        assert len(superadmins) == 0

        # superadmin_exists should return False
        exists = await service.superadmin_exists()
        assert exists is False

    async def test_suspend_user(self, service):
        """Test suspending a user via service."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            status=UserStatus.ACTIVE,
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.update to return updated user
        async def mock_update(user):
            return user

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Suspend the user
        suspended_user = await service.suspend_user(user_id)

        assert suspended_user.status == UserStatus.SUSPENDED
        service.repository.get_by_id.assert_awaited_once_with(user_id.uuid)
        service.repository.update.assert_awaited_once()

    async def test_suspend_user_not_found(self, service):
        """Test that suspending a non-existent user raises EntityNotFoundError."""
        non_existent_id = UserID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.suspend_user(non_existent_id)

        assert "User not found" in str(exc_info.value)
        service.repository.get_by_id.assert_awaited_once_with(non_existent_id.uuid)

    async def test_activate_user(self, service):
        """Test activating a suspended user via service."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock user (suspended)
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            status=UserStatus.SUSPENDED,
        )

        # Mock repository.get_by_id
        service.repository.get_by_id = AsyncMock(return_value=mock_user)

        # Mock repository.update to return updated user
        async def mock_update(user):
            return user

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Activate the user
        activated_user = await service.activate_user(user_id)

        assert activated_user.status == UserStatus.ACTIVE
        service.repository.get_by_id.assert_awaited_once_with(user_id.uuid)
        service.repository.update.assert_awaited_once()

    async def test_activate_user_not_found(self, service):
        """Test that activating a non-existent user raises EntityNotFoundError."""
        non_existent_id = UserID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.activate_user(non_existent_id)

        assert "User not found" in str(exc_info.value)
        service.repository.get_by_id.assert_awaited_once_with(non_existent_id.uuid)
