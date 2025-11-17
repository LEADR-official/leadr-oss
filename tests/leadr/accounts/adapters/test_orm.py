"""Tests for Account and User ORM models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM, UserORM


@pytest.mark.asyncio
class TestAccountORM:
    """Test suite for Account ORM model."""

    async def test_create_account(self, db_session: AsyncSession):
        """Test creating an account in the database."""
        account = AccountORM(
            name="Acme Corporation",
            slug="acme-corp",
            status="active",
        )

        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        assert account.id is not None
        assert account.name == "Acme Corporation"  # type: ignore[comparison-overlap]
        assert account.slug == "acme-corp"  # type: ignore[comparison-overlap]
        assert account.status == "active"  # type: ignore[comparison-overlap]
        assert account.created_at is not None
        assert account.updated_at is not None

    async def test_account_name_unique(self, db_session: AsyncSession, account_orm: AccountORM):
        """Test that account name must be unique."""
        account2 = AccountORM(
            name=account_orm.name,  # Duplicate name
            slug="acme-corp-2",
            status="active",
        )

        db_session.add(account2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_account_slug_unique(self, db_session: AsyncSession, account_orm: AccountORM):
        """Test that account slug must be unique."""
        account2 = AccountORM(
            name="Different Corporation",
            slug=account_orm.slug,  # Duplicate slug
            status="active",
        )

        db_session.add(account2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_account_status_defaults_to_active(self, account_orm: AccountORM):
        """Test that account status defaults to active."""
        assert account_orm.status == "active"  # type: ignore[comparison-overlap]

    async def test_account_timestamps_auto_managed(self, db_session: AsyncSession):
        """Test that timestamps are automatically managed."""
        before = datetime.now(UTC)

        account = AccountORM(
            name="Acme Corporation",
            slug="acme-corp",
            status="active",
        )

        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        after = datetime.now(UTC)

        assert before <= account.created_at <= after
        assert before <= account.updated_at <= after
        # Timestamps are very close but may differ by microseconds due to separate DB calls
        assert abs((account.created_at - account.updated_at).total_seconds()) < 0.1

    async def test_account_deleted_at_defaults_to_none(self, account_orm: AccountORM):
        """Test that deleted_at defaults to None."""
        assert account_orm.deleted_at is None

    async def test_account_deleted_at_can_be_set(self, db_session: AsyncSession):
        """Test that deleted_at can be set and persisted."""
        account = AccountORM(
            name="Acme Corporation",
            slug="acme-corp",
            status="active",
        )

        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        # Set deleted_at
        delete_time = datetime.now(UTC)
        account.deleted_at = delete_time
        await db_session.commit()
        await db_session.refresh(account)

        assert account.deleted_at is not None
        assert abs((account.deleted_at - delete_time).total_seconds()) < 1  # type: ignore[operator]


@pytest.mark.asyncio
class TestUserORM:
    """Test suite for User ORM model."""

    async def test_create_user(self, db_session: AsyncSession, account_orm: AccountORM):
        """Test creating a user in the database."""
        # Create user
        user = UserORM(
            account_id=account_orm.id,
            email="user@example.com",
            display_name="John Doe",
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.account_id == account_orm.id
        assert user.email == "user@example.com"  # type: ignore[comparison-overlap]
        assert user.display_name == "John Doe"  # type: ignore[comparison-overlap]
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_user_email_unique(self, db_session: AsyncSession, user_orm: UserORM):
        """Test that user email must be unique."""
        # Try to create second user with same email
        user2 = UserORM(
            account_id=user_orm.account_id,
            email=user_orm.email,  # Duplicate email
            display_name="Jane Doe",
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_user_foreign_key_to_account(self, db_session: AsyncSession):
        """Test that user has foreign key constraint to account."""
        # Try to create user without account
        user = UserORM(
            account_id=uuid4(),  # Non-existent account
            email="user@example.com",
            display_name="John Doe",
        )

        db_session.add(user)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_user_cascade_delete_with_account(
        self, db_session: AsyncSession, account_orm: AccountORM, user_orm: UserORM
    ):
        """Test that users are deleted when account is deleted."""
        user_id = user_orm.id

        # Delete account
        await db_session.delete(account_orm)
        await db_session.commit()

        # Verify user is also deleted
        from sqlalchemy import select

        result = await db_session.execute(
            select(UserORM).where(UserORM.id == user_id)  # type: ignore[arg-type]
        )
        deleted_user = result.scalar_one_or_none()

        assert deleted_user is None

    async def test_user_timestamps_auto_managed(
        self, db_session: AsyncSession, account_orm: AccountORM
    ):
        """Test that timestamps are automatically managed."""
        before = datetime.now(UTC)

        # Create user
        user = UserORM(
            account_id=account_orm.id,
            email="user@example.com",
            display_name="John Doe",
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        after = datetime.now(UTC)

        assert before <= user.created_at <= after
        assert before <= user.updated_at <= after
        # Timestamps are very close but may differ by microseconds due to separate DB calls
        assert abs((user.created_at - user.updated_at).total_seconds()) < 0.1

    async def test_user_deleted_at_defaults_to_none(self, user_orm: UserORM):
        """Test that deleted_at defaults to None."""
        assert user_orm.deleted_at is None

    async def test_user_deleted_at_can_be_set(
        self, db_session: AsyncSession, account_orm: AccountORM
    ):
        """Test that deleted_at can be set and persisted."""
        # Create user
        user = UserORM(
            account_id=account_orm.id,
            email="user@example.com",
            display_name="John Doe",
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Set deleted_at
        delete_time = datetime.now(UTC)
        user.deleted_at = delete_time
        await db_session.commit()
        await db_session.refresh(user)

        assert user.deleted_at is not None
        assert abs((user.deleted_at - delete_time).total_seconds()) < 1  # type: ignore[operator]
