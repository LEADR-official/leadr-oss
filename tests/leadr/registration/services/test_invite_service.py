"""Tests for invite service."""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User, UserStatus
from leadr.common.domain.ids import AccountID, UserID
from leadr.registration.domain.verification_code import VerificationCode
from leadr.registration.services.invite_service import InviteService


@pytest.mark.asyncio
class TestInviteServiceSendInvite:
    """Test InviteService.send_invite method."""

    async def test_send_invite_creates_new_user(self, db_session: AsyncSession):
        """Test that send_invite creates a new user with INVITED status."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        # No existing user
        mock_user_service.get_user_by_email.return_value = None

        # Mock user creation
        created_user = User(
            id=UserID(),
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.create.return_value = created_user

        # Mock verification code
        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "ABC123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        user = await service.send_invite(
            email="invited@example.com",
            account_id=account_id,
        )

        assert user.status == UserStatus.INVITED
        assert user.email == "invited@example.com"
        mock_user_service.repository.create.assert_called_once()
        mock_verification_service.create_invite_code.assert_called_once()
        mock_email_service.send_invite_email.assert_called_once_with(
            to="invited@example.com",
            account_name="Test Account",
            code="ABC123",
        )

    async def test_send_invite_uses_email_prefix_as_display_name(self, db_session: AsyncSession):
        """Test that display name defaults to email prefix."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account
        mock_user_service.get_user_by_email.return_value = None
        mock_user_service.repository = AsyncMock()

        # Capture the user that gets created
        created_user = None

        async def capture_create(user):
            nonlocal created_user
            created_user = user
            return user

        mock_user_service.repository.create.side_effect = capture_create

        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "ABC123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        await service.send_invite(
            email="john.doe@example.com",
            account_id=account_id,
            display_name=None,
        )

        assert created_user is not None
        assert created_user.display_name == "john.doe"

    async def test_send_invite_uses_custom_display_name(self, db_session: AsyncSession):
        """Test that custom display name is used when provided."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account
        mock_user_service.get_user_by_email.return_value = None
        mock_user_service.repository = AsyncMock()

        created_user = None

        async def capture_create(user):
            nonlocal created_user
            created_user = user
            return user

        mock_user_service.repository.create.side_effect = capture_create

        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "ABC123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        await service.send_invite(
            email="john.doe@example.com",
            account_id=account_id,
            display_name="Custom Name",
        )

        assert created_user is not None
        assert created_user.display_name == "Custom Name"

    async def test_send_invite_empty_display_name_uses_email_prefix(self, db_session: AsyncSession):
        """Test that empty display name falls back to email prefix."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account
        mock_user_service.get_user_by_email.return_value = None
        mock_user_service.repository = AsyncMock()

        created_user = None

        async def capture_create(user):
            nonlocal created_user
            created_user = user
            return user

        mock_user_service.repository.create.side_effect = capture_create

        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "ABC123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        await service.send_invite(
            email="test@example.com",
            account_id=account_id,
            display_name="   ",  # Whitespace only
        )

        assert created_user is not None
        assert created_user.display_name == "test"

    async def test_send_invite_resends_for_existing_invited_user(self, db_session: AsyncSession):
        """Test that invite is resent for existing user with INVITED status."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        # Existing invited user
        existing_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_user_by_email.return_value = existing_user

        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "NEW123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        user = await service.send_invite(
            email="invited@example.com",
            account_id=account_id,
        )

        # Should return existing user, not create new
        assert user == existing_user
        mock_user_service.repository.create.assert_not_called()

        # Should create new verification code
        mock_verification_service.create_invite_code.assert_called_once_with(
            email="invited@example.com",
            user_id=user_id,
        )

        # Should send email
        mock_email_service.send_invite_email.assert_called_once()

    async def test_send_invite_fails_for_active_user(self, db_session: AsyncSession):
        """Test that inviting an active user raises error."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        # Existing active user
        existing_user = User(
            id=UserID(),
            account_id=account_id,
            email="active@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
        )
        mock_user_service.get_user_by_email.return_value = existing_user

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        with pytest.raises(ValueError, match="already exists and is active"):
            await service.send_invite(
                email="active@example.com",
                account_id=account_id,
            )

    async def test_send_invite_email_failure_does_not_fail_invite(self, db_session: AsyncSession):
        """Test that email failure doesn't fail the invite."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_verification_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account
        mock_user_service.get_user_by_email.return_value = None
        mock_user_service.repository = AsyncMock()

        created_user = User(
            id=UserID(),
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.repository.create.return_value = created_user

        mock_verification_code = Mock(spec=VerificationCode)
        mock_verification_code.code = "ABC123"
        mock_verification_service.create_invite_code.return_value = mock_verification_code

        # Email fails
        mock_email_service.send_invite_email.side_effect = Exception("SMTP error")

        service = InviteService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            verification_service=mock_verification_service,
            email_service=mock_email_service,
        )

        # Should not raise
        user = await service.send_invite(
            email="invited@example.com",
            account_id=account_id,
        )

        assert user is not None
        assert user.status == UserStatus.INVITED
