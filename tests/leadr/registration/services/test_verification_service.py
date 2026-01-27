"""Tests for verification service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.user import User
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import UserID
from leadr.config import settings
from leadr.registration.adapters.orm import VerificationCodeTypeEnum
from leadr.registration.domain.verification_code import VerificationCodeType
from leadr.registration.services.verification_service import VerificationService


@pytest.mark.asyncio
class TestVerificationServiceInitiateVerification:
    """Test VerificationService.initiate_verification method."""

    async def test_initiate_verification_creates_code(self, db_session: AsyncSession):
        """Test that initiate_verification creates a verification code."""
        mock_email_service = AsyncMock()
        mock_email_service.send_verification_code = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        await service.initiate_verification("test@example.com")

        # Verify code was created in database
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        assert len(result.items) == 1
        assert result.items[0].email == "test@example.com"
        assert len(result.items[0].code) == 6  # Code should be 6 characters

    async def test_initiate_verification_sends_email(self, db_session: AsyncSession):
        """Test that initiate_verification sends email."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        await service.initiate_verification("test@example.com")

        # Verify email was sent
        mock_email_service.send_verification_code.assert_called_once()
        call_args = mock_email_service.send_verification_code.call_args
        assert call_args[0][0] == "test@example.com"  # Email address
        assert len(call_args[0][1]) == 6  # Verification code

    async def test_initiate_verification_invalidates_old_codes(self, db_session: AsyncSession):
        """Test that initiate_verification invalidates old pending codes."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create initial code
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        first_result = await service.repository.filter(
            email="test@example.com", pagination=pagination
        )
        first_code = first_result.items[0].code

        # Create another code
        await service.initiate_verification("test@example.com")

        # First code should no longer be valid
        valid_code = await service.repository.find_valid_code_by_email(
            "test@example.com", first_code
        )
        assert valid_code is None

        # Should have new valid code
        all_result = await service.repository.filter(
            email="test@example.com", pagination=pagination
        )
        assert len(all_result.items) == 2  # Both codes exist, but only one is valid

    async def test_initiate_verification_sets_expiry(self, db_session: AsyncSession):
        """Test that initiate_verification sets correct expiry time."""

        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        before = datetime.now(UTC)
        await service.initiate_verification("test@example.com")
        after = datetime.now(UTC)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0]

        expected_expiry_min = before + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)
        expected_expiry_max = after + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)

        assert expected_expiry_min <= code.expires_at <= expected_expiry_max


@pytest.mark.asyncio
class TestVerificationServiceVerifyCode:
    """Test VerificationService.verify_code method."""

    async def test_verify_code_success(self, db_session: AsyncSession):
        """Test successful code verification returns token and type."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create verification code
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code

        # Verify the code
        token, code_type = await service.verify_code("test@example.com", code)

        assert token is not None
        assert isinstance(token, str)
        assert code_type == VerificationCodeType.REGISTRATION

    async def test_verify_code_invalid_code(self, db_session: AsyncSession):
        """Test verifying invalid code raises error."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        with pytest.raises(ValueError, match="Invalid or expired verification code"):
            await service.verify_code("test@example.com", "WRONG")

    async def test_verify_code_expired(self, db_session: AsyncSession):
        """Test verifying expired code raises error."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create code and manually expire it
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code_entity = result.items[0]
        code_entity.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await service.repository.update(code_entity)
        await db_session.commit()

        with pytest.raises(ValueError, match="Verification code has expired"):
            await service.verify_code("test@example.com", code_entity.code)

    async def test_verify_code_already_used(self, db_session: AsyncSession):
        """Test verifying already-used code raises error."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify code
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code

        # First verification succeeds
        await service.verify_code("test@example.com", code)

        # Second verification fails (code no longer valid after being used)
        with pytest.raises(ValueError, match="Invalid or expired verification code"):
            await service.verify_code("test@example.com", code)

    async def test_verify_code_marks_as_used(self, db_session: AsyncSession):
        """Test that verify_code marks code as used."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code

        await service.verify_code("test@example.com", code)

        # Code should now be marked as used
        code_entity = await service.repository.find_valid_code_by_email("test@example.com", code)
        assert code_entity is None  # No longer valid

    async def test_verify_code_case_insensitive(self, db_session: AsyncSession):
        """Test that code verification is case insensitive."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code

        # Verify with lowercase version
        token, code_type = await service.verify_code("test@example.com", code.lower())
        assert token is not None
        assert code_type == VerificationCodeType.REGISTRATION


@pytest.mark.asyncio
class TestVerificationServiceValidateToken:
    """Test VerificationService.validate_verification_token method."""

    async def test_validate_token_success(self, db_session: AsyncSession):
        """Test validating a valid token returns email."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify code to get token
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code
        token, _ = await service.verify_code("test@example.com", code)

        # Validate the token
        email = service.validate_verification_token(token)
        assert email == "test@example.com"

    async def test_validate_token_invalid(self, db_session: AsyncSession):
        """Test validating invalid token raises error."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        with pytest.raises(ValueError, match="Invalid verification token"):
            service.validate_verification_token("invalid.token.here")

    async def test_validate_token_expired(self, db_session: AsyncSession):
        """Test validating expired token raises error."""

        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create an expired token
        now = datetime.now(UTC)
        expired_payload = {
            "email": "test@example.com",
            "type": "registration",
            "iat": (now - timedelta(hours=1)).timestamp(),
            "exp": (now - timedelta(seconds=1)).timestamp(),
        }
        expired_token = jwt.encode(expired_payload, settings.API_KEY_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="Verification token has expired"):
            service.validate_verification_token(expired_token)

    async def test_validate_token_wrong_type(self, db_session: AsyncSession):
        """Test validating token with wrong type raises error."""

        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create a token with wrong type
        now = datetime.now(UTC)
        wrong_type_payload = {
            "email": "test@example.com",
            "type": "not_registration",
            "iat": now.timestamp(),
            "exp": (now + timedelta(minutes=10)).timestamp(),
        }
        wrong_type_token = jwt.encode(
            wrong_type_payload, settings.API_KEY_SECRET, algorithm="HS256"
        )

        with pytest.raises(ValueError, match="Invalid token type"):
            service.validate_verification_token(wrong_type_token)

    async def test_validate_token_missing_email(self, db_session: AsyncSession):
        """Test validating token without email raises error."""

        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create a token without email
        now = datetime.now(UTC)
        no_email_payload = {
            "type": "registration",
            "iat": now.timestamp(),
            "exp": (now + timedelta(minutes=10)).timestamp(),
        }
        no_email_token = jwt.encode(no_email_payload, settings.API_KEY_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="Missing email in token"):
            service.validate_verification_token(no_email_token)


@pytest.mark.asyncio
class TestVerificationServiceCreateInviteCode:
    """Test VerificationService.create_invite_code method."""

    async def test_create_invite_code_success(self, db_session: AsyncSession, test_user: User):
        """Test creating an invite code."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )

        assert code is not None
        assert code.email == "invited@example.com"
        assert code.code_type == VerificationCodeType.INVITE
        assert code.user_id == test_user.id
        assert len(code.code) == 6

    async def test_create_invite_code_sets_24h_expiry(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that invite codes have 24 hour expiry."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        before = datetime.now(UTC)
        code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )
        after = datetime.now(UTC)

        expected_expiry_min = before + timedelta(seconds=settings.INVITE_CODE_EXPIRY_SECONDS)
        expected_expiry_max = after + timedelta(seconds=settings.INVITE_CODE_EXPIRY_SECONDS)

        assert expected_expiry_min <= code.expires_at <= expected_expiry_max

    async def test_create_invite_code_invalidates_old_codes(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that creating invite code invalidates old pending codes."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create first invite code
        first_code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )

        # Create second invite code
        second_code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )

        # First code should no longer be valid
        valid_code = await service.repository.find_valid_code_by_email(
            "invited@example.com",
            first_code.code,
            code_type=VerificationCodeTypeEnum.INVITE,
        )
        assert valid_code is None

        # Second code should be valid
        valid_code = await service.repository.find_valid_code_by_email(
            "invited@example.com",
            second_code.code,
            code_type=VerificationCodeTypeEnum.INVITE,
        )
        assert valid_code is not None


@pytest.mark.asyncio
class TestVerificationServiceVerifyInviteCode:
    """Test VerificationService.verify_code for invite codes."""

    async def test_verify_invite_code_returns_token_with_user_id(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that verifying invite code returns token containing user_id and INVITE type."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create invite code
        code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )

        # Verify the code
        token, code_type = await service.verify_code("invited@example.com", code.code)

        # Should return INVITE type
        assert code_type == VerificationCodeType.INVITE

        # Token should contain user_id
        payload = jwt.decode(token, settings.API_KEY_SECRET, algorithms=["HS256"])
        assert payload["type"] == "invite"
        assert payload["user_id"] == str(test_user.id.uuid)


@pytest.mark.asyncio
class TestVerificationServiceGetInviteUserId:
    """Test VerificationService.get_invite_user_id method."""

    async def test_get_invite_user_id_returns_user_id_for_invite_token(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that get_invite_user_id returns user_id from invite token."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify invite code to get token
        code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )
        token, _ = await service.verify_code("invited@example.com", code.code)

        # Get user_id from token
        result_user_id = service.get_invite_user_id(token)

        assert result_user_id is not None
        assert result_user_id == test_user.id

    async def test_get_invite_user_id_returns_none_for_registration_token(
        self, db_session: AsyncSession
    ):
        """Test that get_invite_user_id returns None for registration token."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify registration code
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code
        token, _ = await service.verify_code("test@example.com", code)

        # Should return None for registration token
        result_user_id = service.get_invite_user_id(token)

        assert result_user_id is None

    async def test_get_invite_user_id_raises_for_invalid_token(self, db_session: AsyncSession):
        """Test that get_invite_user_id raises ValueError for invalid token."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        with pytest.raises(ValueError, match="Invalid verification token"):
            service.get_invite_user_id("invalid.token.here")

    async def test_get_invite_user_id_raises_for_expired_token(self, db_session: AsyncSession):
        """Test that get_invite_user_id raises ValueError for expired token."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)
        user_id = UserID()

        # Create an expired invite token
        now = datetime.now(UTC)
        expired_payload = {
            "email": "test@example.com",
            "type": "invite",
            "user_id": str(user_id.uuid),
            "iat": (now - timedelta(hours=1)).timestamp(),
            "exp": (now - timedelta(seconds=1)).timestamp(),
        }
        expired_token = jwt.encode(expired_payload, settings.API_KEY_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="Verification token has expired"):
            service.get_invite_user_id(expired_token)

    async def test_get_invite_user_id_returns_none_for_invite_token_without_user_id(
        self, db_session: AsyncSession
    ):
        """Test that get_invite_user_id returns None for invite token missing user_id."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create an invite token without user_id
        now = datetime.now(UTC)
        payload = {
            "email": "test@example.com",
            "type": "invite",  # Invite type but no user_id
            "iat": now.timestamp(),
            "exp": (now + timedelta(minutes=10)).timestamp(),
        }
        token = jwt.encode(payload, settings.API_KEY_SECRET, algorithm="HS256")

        result_user_id = service.get_invite_user_id(token)

        assert result_user_id is None


@pytest.mark.asyncio
class TestVerificationServiceValidateInviteToken:
    """Test VerificationService.validate_verification_token for invite tokens."""

    async def test_validate_invite_token_success(self, db_session: AsyncSession, test_user: User):
        """Test validating an invite token returns email."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify invite code
        code = await service.create_invite_code(
            email="invited@example.com",
            user_id=test_user.id,
        )
        token, _ = await service.verify_code("invited@example.com", code.code)

        # Validate the token
        email = service.validate_verification_token(token)

        assert email == "invited@example.com"
