"""Tests for User domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.accounts.domain.user import User, UserStatus
from leadr.common.domain.ids import AccountID, UserID


class TestUser:
    """Test suite for User domain model."""

    def test_create_user_with_valid_data(self):
        """Test creating a user with all required fields."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.id == user_id
        assert user.account_id == account_id
        assert user.email == "user@example.com"
        assert user.display_name == "John Doe"
        assert user.created_at == now
        assert user.updated_at == now

    def test_user_email_required(self):
        """Test that user email is required."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            User(  # type: ignore[call-arg]
                id=user_id,
                account_id=account_id,
                display_name="John Doe",
                created_at=now,
                updated_at=now,
            )

        assert "email" in str(exc_info.value)

    def test_user_display_name_required(self):
        """Test that user display name is required."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            User(  # type: ignore[call-arg]
                id=user_id,
                account_id=account_id,
                email="user@example.com",
                created_at=now,
                updated_at=now,
            )

        assert "display_name" in str(exc_info.value)

    def test_user_account_id_required(self):
        """Test that user account_id is required."""
        user_id = UserID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            User(  # type: ignore[call-arg]
                id=user_id,
                email="user@example.com",
                display_name="John Doe",
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_user_equality_based_on_id(self):
        """Test that user equality is based on ID."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user1 = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        user2 = User(
            id=user_id,
            account_id=account_id,
            email="different@example.com",
            display_name="Different Name",
            created_at=now,
            updated_at=now,
        )

        assert user1 == user2

    def test_user_inequality_different_ids(self):
        """Test that users with different IDs are not equal."""
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user1 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        user2 = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user1 != user2

    def test_user_is_hashable(self):
        """Test that user can be used in sets and as dict keys."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        user_set = {user}  # type: ignore[var-annotated]
        assert user in user_set

        # Should work as dict key
        user_dict = {user: "value"}  # type: ignore[dict-item]
        assert user_dict[user] == "value"

    def test_user_immutability_of_id(self):
        """Test that user ID cannot be changed after creation."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        new_id = UserID(uuid4())

        with pytest.raises(ValidationError):
            user.id = new_id

    def test_user_immutability_of_account_id(self):
        """Test that user account_id cannot be changed after creation."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        new_account_id = AccountID(uuid4())

        with pytest.raises(ValidationError):
            user.account_id = new_account_id

    def test_user_soft_delete(self):
        """Test that user can be soft-deleted."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.is_deleted is False
        assert user.deleted_at is None

        user.soft_delete()

        assert user.is_deleted is True
        assert user.deleted_at is not None

    def test_user_restore(self):
        """Test that soft-deleted user can be restored."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        user.soft_delete()
        assert user.is_deleted is True

        user.restore()
        assert user.is_deleted is False
        assert user.deleted_at is None

    def test_user_super_admin_defaults_to_false(self):
        """Test that super_admin defaults to False when not specified."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.super_admin is False

    def test_user_can_be_created_as_super_admin(self):
        """Test that super_admin can be set to True."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        assert user.super_admin is True

    def test_user_super_admin_can_be_updated(self):
        """Test that super_admin flag can be updated after creation."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.super_admin is False

        # Update to superadmin
        user.super_admin = True
        assert user.super_admin is True

        # Can be revoked
        user.super_admin = False
        assert user.super_admin is False


class TestUserStatus:
    """Test suite for UserStatus enum and status field."""

    def test_user_status_enum_values(self):
        """Test that UserStatus enum has expected values."""
        assert UserStatus.INVITED.value == "invited"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.SUSPENDED.value == "suspended"

    def test_user_status_defaults_to_active(self):
        """Test that user status defaults to ACTIVE when not specified."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.status == UserStatus.ACTIVE

    def test_user_can_be_created_with_invited_status(self):
        """Test that user can be created with INVITED status."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="Invited User",
            status=UserStatus.INVITED,
            created_at=now,
            updated_at=now,
        )

        assert user.status == UserStatus.INVITED

    def test_user_can_be_created_with_suspended_status(self):
        """Test that user can be created with SUSPENDED status."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="suspended@example.com",
            display_name="Suspended User",
            status=UserStatus.SUSPENDED,
            created_at=now,
            updated_at=now,
        )

        assert user.status == UserStatus.SUSPENDED

    def test_activate_changes_status_to_active(self):
        """Test that activate() changes status from INVITED to ACTIVE."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="Invited User",
            status=UserStatus.INVITED,
            created_at=now,
            updated_at=now,
        )

        assert user.status == UserStatus.INVITED

        user.activate()

        assert user.status == UserStatus.ACTIVE

    def test_activate_from_suspended_status(self):
        """Test that activate() changes status from SUSPENDED to ACTIVE."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="suspended@example.com",
            display_name="Suspended User",
            status=UserStatus.SUSPENDED,
            created_at=now,
            updated_at=now,
        )

        user.activate()

        assert user.status == UserStatus.ACTIVE

    def test_activate_already_active_is_idempotent(self):
        """Test that activate() on an already active user is a no-op."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        user.activate()

        assert user.status == UserStatus.ACTIVE

    def test_suspend_changes_status_to_suspended(self):
        """Test that suspend() changes status to SUSPENDED."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        user.suspend()

        assert user.status == UserStatus.SUSPENDED

    def test_is_invited_property(self):
        """Test is_invited property returns True for INVITED status."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        invited_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="Invited User",
            status=UserStatus.INVITED,
            created_at=now,
            updated_at=now,
        )

        active_user = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="active@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        assert invited_user.is_invited is True
        assert active_user.is_invited is False

    def test_is_active_property(self):
        """Test is_active property returns True for ACTIVE status."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        active_user = User(
            id=user_id,
            account_id=account_id,
            email="active@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        invited_user = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="invited@example.com",
            display_name="Invited User",
            status=UserStatus.INVITED,
            created_at=now,
            updated_at=now,
        )

        assert active_user.is_active is True
        assert invited_user.is_active is False

    def test_is_suspended_property(self):
        """Test is_suspended property returns True for SUSPENDED status."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        suspended_user = User(
            id=user_id,
            account_id=account_id,
            email="suspended@example.com",
            display_name="Suspended User",
            status=UserStatus.SUSPENDED,
            created_at=now,
            updated_at=now,
        )

        active_user = User(
            id=UserID(uuid4()),
            account_id=account_id,
            email="active@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        assert suspended_user.is_suspended is True
        assert active_user.is_suspended is False


class TestUserIsOwner:
    """Test suite for is_owner field."""

    def test_is_owner_defaults_to_false(self):
        """Test that is_owner defaults to False when not specified."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.is_owner is False

    def test_user_can_be_created_as_owner(self):
        """Test that user can be created with is_owner=True."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="owner@example.com",
            display_name="Account Owner",
            is_owner=True,
            created_at=now,
            updated_at=now,
        )

        assert user.is_owner is True

    def test_is_owner_can_be_updated(self):
        """Test that is_owner flag can be updated after creation."""
        user_id = UserID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert user.is_owner is False

        user.is_owner = True
        assert user.is_owner is True

        user.is_owner = False
        assert user.is_owner is False
