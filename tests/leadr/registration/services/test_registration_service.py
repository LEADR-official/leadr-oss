"""Tests for registration service."""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User, UserStatus
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.geoip import GeoInfo
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.services.registration_service import RegistrationService


@pytest.mark.asyncio
class TestRegistrationServiceCompleteRegistration:
    """Test RegistrationService.complete_registration method."""

    async def test_complete_registration_success(self, db_session: AsyncSession):
        """Test successful registration flow with geo info."""
        # Mock all dependencies
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Setup mock returns
        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            timezone="America/New_York",
            country="US",
            city="New York",
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_test_key_123")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        geo_info = GeoInfo(timezone="America/New_York", country="US", city="New York")
        account, user, api_key = await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            geo_info=geo_info,
        )

        assert account == mock_account
        assert user == mock_user
        assert api_key == "ldr_test_key_123"

        # Verify all services were called correctly
        mock_verification_service.validate_verification_token.assert_called_once_with("valid_token")
        mock_account_service.create_account.assert_called_once_with(
            name="Test Account",
            slug="test-account",
            timezone="America/New_York",
            country="US",
            city="New York",
        )
        mock_user_service.create_user.assert_called_once_with(
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
            is_owner=True,
        )
        mock_api_key_service.create_api_key.assert_called_once()

    async def test_complete_registration_without_geo_info(self, db_session: AsyncSession):
        """Test registration without geo info passes None for geo fields."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            geo_info=None,  # No geo info
        )

        # Verify geo fields are None when geo_info is not provided
        mock_account_service.create_account.assert_called_once_with(
            name="Test Account",
            slug="test-account",
            timezone=None,
            country=None,
            city=None,
        )

    async def test_complete_registration_with_empty_geo_info(self, db_session: AsyncSession):
        """Test registration with empty geo info passes None for geo fields."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        # GeoInfo with all None fields (e.g., when GeoIP lookup fails)
        geo_info = GeoInfo(timezone=None, country=None, city=None)
        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            geo_info=geo_info,
        )

        # Verify geo fields are None when geo_info has all None fields
        mock_account_service.create_account.assert_called_once_with(
            name="Test Account",
            slug="test-account",
            timezone=None,
            country=None,
            city=None,
        )

    async def test_complete_registration_auto_generates_slug(self, db_session: AsyncSession):
        """Test that slug is auto-generated when not provided."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account
        mock_account_service.get_account_by_slug.return_value = None  # Slug available

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug=None,  # No slug provided
        )

        # Verify slug was generated
        create_call = mock_account_service.create_account.call_args
        assert create_call.kwargs["slug"] is not None

    async def test_complete_registration_with_jam_code(self, db_session: AsyncSession):
        """Test registration with a valid jam code."""

        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        mock_jam_code = JamCode(
            code="PROMO2024", description="Test promo", features={"premium": True}
        )
        mock_jam_code_service.validate_and_get_jam_code.return_value = mock_jam_code
        mock_jam_code_service.redeem_jam_code.return_value = Mock()

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            jam_code="PROMO2024",
        )

        # Verify jam code was validated and redeemed
        mock_jam_code_service.validate_and_get_jam_code.assert_called_once_with("PROMO2024")
        mock_jam_code_service.redeem_jam_code.assert_called_once_with(
            jam_code=mock_jam_code, account_id=mock_account.id, meta={"premium": True}
        )

    async def test_complete_registration_invalid_jam_code(self, db_session: AsyncSession):
        """Test registration with invalid jam code raises error."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None
        mock_jam_code_service.validate_and_get_jam_code.return_value = None  # Invalid code

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        with pytest.raises(ValueError, match="Invalid or expired jam code"):
            await service.complete_registration(
                verification_token="valid_token",
                account_name="Test Account",
                account_slug="test-account",
                jam_code="INVALID",
            )

    async def test_complete_registration_invalid_token(self, db_session: AsyncSession):
        """Test registration with invalid verification token raises error."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.side_effect = ValueError(
            "Invalid token"
        )

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        with pytest.raises(ValueError, match="Invalid token"):
            await service.complete_registration(
                verification_token="invalid_token",
                account_name="Test Account",
                account_slug="test-account",
            )

    async def test_complete_registration_sends_welcome_email(self, db_session: AsyncSession):
        """Test that registration sends welcome email."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
        )

        # Verify welcome email was sent
        mock_email_service.send_welcome_email.assert_called_once_with(
            to="test@example.com",
            user_name="test",
            account_name="Test Account",
            account_slug="test-account",
        )

    async def test_complete_registration_email_failure_doesnt_fail_registration(
        self, db_session: AsyncSession
    ):
        """Test that email send failure doesn't fail registration."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        # Email send fails
        mock_email_service.send_welcome_email.side_effect = Exception("Email failed")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        # Should not raise exception
        account, user, api_key = await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
        )

        # Registration should still succeed
        assert account is not None
        assert user is not None
        assert api_key is not None

    async def test_complete_registration_uses_email_prefix_as_display_name(
        self, db_session: AsyncSession
    ):
        """Test that display name is set from email prefix when not provided."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "john.doe@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="john.doe@example.com",
            display_name="john.doe",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            display_name=None,  # Explicitly not provided
        )

        # Verify display name was set from email prefix
        create_user_call = mock_user_service.create_user.call_args
        assert create_user_call.kwargs["display_name"] == "john.doe"

    async def test_complete_registration_with_custom_display_name(self, db_session: AsyncSession):
        """Test that custom display name is used when provided."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "john.doe@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="john.doe@example.com",
            display_name="Custom Name",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            display_name="Custom Name",
        )

        # Verify custom display name was used
        create_user_call = mock_user_service.create_user.call_args
        assert create_user_call.kwargs["display_name"] == "Custom Name"

    async def test_complete_registration_with_empty_display_name_uses_email_prefix(
        self, db_session: AsyncSession
    ):
        """Test that empty string display name falls back to email prefix."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            display_name="",  # Empty string
        )

        # Verify display name was set from email prefix
        create_user_call = mock_user_service.create_user.call_args
        assert create_user_call.kwargs["display_name"] == "test"

    async def test_complete_registration_with_whitespace_display_name_uses_email_prefix(
        self, db_session: AsyncSession
    ):
        """Test that whitespace-only display name falls back to email prefix."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None

        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.create_account.return_value = mock_account

        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_user_service.create_user.return_value = mock_user
        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_token",
            account_name="Test Account",
            account_slug="test-account",
            display_name="   ",  # Whitespace only
        )

        # Verify display name was set from email prefix
        create_user_call = mock_user_service.create_user.call_args
        assert create_user_call.kwargs["display_name"] == "test"


@pytest.mark.asyncio
class TestRegistrationServiceGenerateUniqueSlug:
    """Test RegistrationService._generate_unique_slug method."""

    async def test_generate_unique_slug_first_try(self, db_session: AsyncSession):
        """Test generating unique slug on first try."""
        mock_account_service = AsyncMock()
        mock_account_service.get_account_by_slug.return_value = None  # Slug available

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=AsyncMock(),
            api_key_service=AsyncMock(),
            verification_service=Mock(),
            jam_code_service=AsyncMock(),
            email_service=AsyncMock(),
        )

        slug = await service._generate_unique_slug("Test Account")

        assert slug == "test-account"
        mock_account_service.get_account_by_slug.assert_called_once_with("test-account")

    async def test_generate_unique_slug_with_collision(self, db_session: AsyncSession):
        """Test generating unique slug when first choice is taken."""
        mock_account_service = AsyncMock()

        # First slug is taken, second is available
        mock_account_service.get_account_by_slug.side_effect = [
            Mock(),  # First slug exists
            None,  # Second slug available
        ]

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=AsyncMock(),
            api_key_service=AsyncMock(),
            verification_service=Mock(),
            jam_code_service=AsyncMock(),
            email_service=AsyncMock(),
        )

        slug = await service._generate_unique_slug("Test Account")

        assert slug == "test-account-1"

    async def test_generate_unique_slug_multiple_collisions(self, db_session: AsyncSession):
        """Test generating unique slug with multiple collisions."""
        mock_account_service = AsyncMock()

        # First three slugs are taken, fourth is available
        mock_account_service.get_account_by_slug.side_effect = [
            Mock(),  # test-account exists
            Mock(),  # test-account-1 exists
            Mock(),  # test-account-2 exists
            None,  # test-account-3 available
        ]

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=AsyncMock(),
            api_key_service=AsyncMock(),
            verification_service=Mock(),
            jam_code_service=AsyncMock(),
            email_service=AsyncMock(),
        )

        slug = await service._generate_unique_slug("Test Account")

        assert slug == "test-account-3"

    async def test_generate_unique_slug_safety_limit(self, db_session: AsyncSession):
        """Test that slug generation has safety limit."""
        mock_account_service = AsyncMock()

        # Always return existing account (simulate many collisions)
        mock_account_service.get_account_by_slug.return_value = Mock()

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=AsyncMock(),
            api_key_service=AsyncMock(),
            verification_service=Mock(),
            jam_code_service=AsyncMock(),
            email_service=AsyncMock(),
        )

        slug = await service._generate_unique_slug("Test Account")

        # Should eventually return a slug with random suffix
        assert slug.startswith("test-account-")
        assert len(slug) >= len("test-account-xxxx")  # Has random suffix (4 chars)


@pytest.mark.asyncio
class TestRegistrationServiceInviteFlow:
    """Test RegistrationService invite completion flow."""

    async def test_complete_registration_invite_flow_activates_user(self, db_session: AsyncSession):
        """Test that invite flow activates the invited user and ignores geo_info."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "invited@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.update.return_value = mock_user

        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_invite_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        # Pass geo_info even for invite flow - it should be ignored
        geo_info = GeoInfo(timezone="America/New_York", country="US", city="New York")
        account, user, api_key = await service.complete_registration(
            verification_token="valid_invite_token",
            account_name=None,  # Not needed for invite flow
            geo_info=geo_info,  # Should be ignored
        )

        assert api_key == "ldr_invite_key"
        # Should not create new account (geo_info is ignored)
        mock_account_service.create_account.assert_not_called()
        # Should not create new user
        mock_user_service.create_user.assert_not_called()
        # Should update user
        mock_user_service.repository.update.assert_called_once()

    async def test_complete_registration_invite_flow_updates_display_name(
        self, db_session: AsyncSession
    ):
        """Test that invite flow can update display name."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "invited@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.update.return_value = mock_user

        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_invite_token",
            display_name="New Display Name",
        )

        # User's display_name should have been updated
        assert mock_user.display_name == "New Display Name"

    async def test_complete_registration_invite_flow_keeps_display_name_if_not_provided(
        self, db_session: AsyncSession
    ):
        """Test that invite flow keeps existing display name if not provided."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "invited@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="Original Name",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.update.return_value = mock_user

        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_invite_token",
            display_name=None,
        )

        # User's display_name should remain unchanged
        assert mock_user.display_name == "Original Name"

    async def test_complete_registration_invite_flow_fails_for_non_invited_user(
        self, db_session: AsyncSession
    ):
        """Test that invite flow fails if user is not in INVITED status."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "active@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        # User is already ACTIVE, not INVITED
        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="active@example.com",
            display_name="Active User",
            status=UserStatus.ACTIVE,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        with pytest.raises(ValueError, match="not in invited status"):
            await service.complete_registration(
                verification_token="valid_invite_token",
            )

    async def test_complete_registration_invite_flow_sends_welcome_email(
        self, db_session: AsyncSession
    ):
        """Test that invite flow sends welcome email."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "invited@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.update.return_value = mock_user

        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        await service.complete_registration(
            verification_token="valid_invite_token",
        )

        mock_email_service.send_welcome_email.assert_called_once_with(
            to="invited@example.com",
            user_name="invited",
            account_name="Test Account",
            account_slug="test-account",
        )

    async def test_complete_registration_invite_flow_email_failure_doesnt_fail(
        self, db_session: AsyncSession
    ):
        """Test that email failure doesn't fail invite completion."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        account_id = AccountID()
        user_id = UserID()

        mock_verification_service.validate_verification_token.return_value = "invited@example.com"
        mock_verification_service.get_invite_user_id.return_value = user_id

        mock_account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_account_service.get_by_id_or_raise.return_value = mock_account

        mock_user = User(
            id=user_id,
            account_id=account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_user_service.get_by_id_or_raise.return_value = mock_user
        mock_user_service.repository = AsyncMock()
        mock_user_service.repository.update.return_value = mock_user

        mock_api_key_service.create_api_key.return_value = (Mock(), "ldr_key")

        # Email fails
        mock_email_service.send_welcome_email.side_effect = Exception("SMTP error")

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        # Should not raise
        account, user, api_key = await service.complete_registration(
            verification_token="valid_invite_token",
        )

        assert account is not None
        assert user is not None
        assert api_key is not None

    async def test_complete_registration_requires_account_name_for_new_registration(
        self, db_session: AsyncSession
    ):
        """Test that account_name is required for new registration (not invite)."""
        mock_account_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_api_key_service = AsyncMock()
        mock_verification_service = Mock()
        mock_jam_code_service = AsyncMock()
        mock_email_service = AsyncMock()

        mock_verification_service.validate_verification_token.return_value = "test@example.com"
        mock_verification_service.get_invite_user_id.return_value = None  # Not an invite

        service = RegistrationService(
            db=db_session,
            account_service=mock_account_service,
            user_service=mock_user_service,
            api_key_service=mock_api_key_service,
            verification_service=mock_verification_service,
            jam_code_service=mock_jam_code_service,
            email_service=mock_email_service,
        )

        with pytest.raises(ValueError, match="Account name is required"):
            await service.complete_registration(
                verification_token="valid_token",
                account_name=None,  # Missing account name
            )
