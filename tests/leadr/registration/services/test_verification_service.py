"""Tests for verification service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.config import settings
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
        codes = await service.repository.filter(email="test@example.com")
        assert len(codes) == 1
        assert codes[0].email == "test@example.com"
        assert len(codes[0].code) == 6  # Code should be 6 characters

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
        first_codes = await service.repository.filter(email="test@example.com")
        first_code = first_codes[0].code

        # Create another code
        await service.initiate_verification("test@example.com")

        # First code should no longer be valid
        valid_code = await service.repository.find_valid_code_by_email(
            "test@example.com", first_code
        )
        assert valid_code is None

        # Should have new valid code
        all_codes = await service.repository.filter(email="test@example.com")
        assert len(all_codes) == 2  # Both codes exist, but only one is valid

    async def test_initiate_verification_sets_expiry(self, db_session: AsyncSession):
        """Test that initiate_verification sets correct expiry time."""

        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        before = datetime.now(UTC)
        await service.initiate_verification("test@example.com")
        after = datetime.now(UTC)

        codes = await service.repository.filter(email="test@example.com")
        code = codes[0]

        expected_expiry_min = before + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)
        expected_expiry_max = after + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)

        assert expected_expiry_min <= code.expires_at <= expected_expiry_max


@pytest.mark.asyncio
class TestVerificationServiceVerifyCode:
    """Test VerificationService.verify_code method."""

    async def test_verify_code_success(self, db_session: AsyncSession):
        """Test successful code verification returns token."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create verification code
        await service.initiate_verification("test@example.com")
        codes = await service.repository.filter(email="test@example.com")
        code = codes[0].code

        # Verify the code
        token = await service.verify_code("test@example.com", code)

        assert token is not None
        assert isinstance(token, str)

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
        codes = await service.repository.filter(email="test@example.com")
        code_entity = codes[0]
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
        codes = await service.repository.filter(email="test@example.com")
        code = codes[0].code

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
        codes = await service.repository.filter(email="test@example.com")
        code = codes[0].code

        await service.verify_code("test@example.com", code)

        # Code should now be marked as used
        code_entity = await service.repository.find_valid_code_by_email("test@example.com", code)
        assert code_entity is None  # No longer valid

    async def test_verify_code_case_insensitive(self, db_session: AsyncSession):
        """Test that code verification is case insensitive."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        await service.initiate_verification("test@example.com")
        codes = await service.repository.filter(email="test@example.com")
        code = codes[0].code

        # Verify with lowercase version
        token = await service.verify_code("test@example.com", code.lower())
        assert token is not None


@pytest.mark.asyncio
class TestVerificationServiceValidateToken:
    """Test VerificationService.validate_verification_token method."""

    async def test_validate_token_success(self, db_session: AsyncSession):
        """Test validating a valid token returns email."""
        mock_email_service = AsyncMock()

        service = VerificationService(db_session, mock_email_service)

        # Create and verify code to get token
        await service.initiate_verification("test@example.com")
        codes = await service.repository.filter(email="test@example.com")
        code = codes[0].code
        token = await service.verify_code("test@example.com", code)

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
        import jwt

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
        import jwt

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
        import jwt

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
