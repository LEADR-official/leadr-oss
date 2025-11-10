"""Tests for Account domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.accounts.domain.account import Account, AccountStatus


class TestAccount:
    """Test suite for Account domain model."""

    def test_create_account_with_valid_data(self):
        """Test creating an account with all required fields."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        assert account.id == account_id
        assert account.name == "Acme Corporation"
        assert account.slug == "acme-corp"
        assert account.status == AccountStatus.ACTIVE
        assert account.created_at == now
        assert account.updated_at == now

    def test_create_account_defaults_to_active_status(self):
        """Test that account status defaults to ACTIVE."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        assert account.status == AccountStatus.ACTIVE

    def test_account_name_required(self):
        """Test that account name is required."""
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Account(  # type: ignore[call-arg]
                id=account_id,
                slug="acme-corp",
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_account_slug_required(self):
        """Test that account slug is required."""
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Account(  # type: ignore[call-arg]
                id=account_id,
                name="Acme Corporation",
                created_at=now,
                updated_at=now,
            )

        assert "slug" in str(exc_info.value)

    def test_account_equality_based_on_id(self):
        """Test that account equality is based on ID."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account1 = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        account2 = Account(
            id=account_id,
            name="Different Name",
            slug="different-slug",
            created_at=now,
            updated_at=now,
        )

        assert account1 == account2

    def test_account_inequality_different_ids(self):
        """Test that accounts with different IDs are not equal."""
        now = datetime.now(UTC)

        account1 = Account(
            id=uuid4(),
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        account2 = Account(
            id=uuid4(),
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        assert account1 != account2

    def test_account_is_hashable(self):
        """Test that account can be used in sets and as dict keys."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        account_set = {account}  # type: ignore[var-annotated]
        assert account in account_set

        # Should work as dict key
        account_dict = {account: "value"}  # type: ignore[dict-item]
        assert account_dict[account] == "value"

    def test_suspend_account(self):
        """Test suspending an active account."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        account.suspend()

        assert account.status == AccountStatus.SUSPENDED

    def test_activate_account(self):
        """Test activating a suspended account."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.SUSPENDED,
            created_at=now,
            updated_at=now,
        )

        account.activate()

        assert account.status == AccountStatus.ACTIVE

    def test_account_immutability_of_id(self):
        """Test that account ID cannot be changed after creation."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            account.id = new_id

    def test_account_soft_delete(self):
        """Test that account can be soft-deleted."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        assert account.is_deleted is False
        assert account.deleted_at is None

        account.soft_delete()

        assert account.is_deleted is True
        assert account.deleted_at is not None

    def test_account_restore(self):
        """Test that soft-deleted account can be restored."""
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            created_at=now,
            updated_at=now,
        )

        account.soft_delete()
        assert account.is_deleted is True

        account.restore()
        assert account.is_deleted is False
        assert account.deleted_at is None
