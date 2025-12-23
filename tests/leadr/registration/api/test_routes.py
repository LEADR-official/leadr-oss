"""Tests for registration API routes."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.auth.dependencies import require_admin_auth
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, UserID
from leadr.infra.email.service import EmailService
from leadr.registration.services.dependencies import (
    get_email_service,
    get_registration_service,
    get_verification_service,
)
from leadr.registration.services.jam_code_service import JamCodeService
from leadr.registration.services.verification_service import VerificationService


@pytest.mark.asyncio
class TestInitiateRegistration:
    """Test POST /register/initiate endpoint."""

    async def test_initiate_registration_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful registration initiation."""
        # Mock email service to prevent actual email sending
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_verification_code = AsyncMock()

        # Override both email service and verification service
        async def mock_email_service_dep():
            return mock_email_service

        async def mock_verification_service_dep():
            return VerificationService(db_session, email_service=mock_email_service)

        app.dependency_overrides[get_email_service] = mock_email_service_dep
        app.dependency_overrides[get_verification_service] = mock_verification_service_dep

        response = await client.post(
            "/register/initiate",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Verification code sent to email"
        assert data["code_expires_in"] == 600

        app.dependency_overrides.clear()

    async def test_initiate_registration_invalid_email(self, client: AsyncClient):
        """Test initiation with invalid email format."""
        response = await client.post(
            "/register/initiate",
            json={"email": "not-an-email"},
        )

        # Pydantic validates email format and returns 422
        assert response.status_code == 422

    async def test_initiate_registration_prevents_enumeration(self, client: AsyncClient):
        """Test that errors don't reveal if email exists."""
        # Even if service fails, should return success to prevent enumeration
        response = await client.post(
            "/register/initiate",
            json={"email": "any@example.com"},
        )

        assert response.status_code == 201


@pytest.mark.asyncio
class TestVerifyCode:
    """Test POST /register/verify endpoint."""

    async def test_verify_code_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful code verification."""
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_verification_code = AsyncMock()

        async def mock_email_service_dep():
            return mock_email_service

        async def mock_verification_service_dep():
            return VerificationService(db_session, email_service=mock_email_service)

        app.dependency_overrides[get_email_service] = mock_email_service_dep
        app.dependency_overrides[get_verification_service] = mock_verification_service_dep

        # Create verification code
        service = VerificationService(db_session, mock_email_service)
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code

        # Verify the code
        response = await client.post(
            "/register/verify",
            json={"email": "test@example.com", "code": code},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verification_token" in data
        assert data["expires_in"] == 600

        app.dependency_overrides.clear()

    async def test_verify_code_invalid(self, client: AsyncClient):
        """Test verifying invalid code."""
        response = await client.post(
            "/register/verify",
            json={"email": "test@example.com", "code": "WRONG"},
        )

        assert response.status_code == 422

    async def test_verify_code_already_used(self, client: AsyncClient, db_session: AsyncSession):
        """Test verifying already-used code."""
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_verification_code = AsyncMock()

        async def mock_email_service_dep():
            return mock_email_service

        async def mock_verification_service_dep():
            return VerificationService(db_session, email_service=mock_email_service)

        app.dependency_overrides[get_email_service] = mock_email_service_dep
        app.dependency_overrides[get_verification_service] = mock_verification_service_dep

        # Create and use code
        service = VerificationService(db_session, mock_email_service)
        await service.initiate_verification("test@example.com")
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.repository.filter(email="test@example.com", pagination=pagination)
        code = result.items[0].code
        await service.verify_code("test@example.com", code)

        # Try to verify again
        response = await client.post(
            "/register/verify",
            json={"email": "test@example.com", "code": code},
        )

        assert response.status_code == 400
        response_data = response.json()
        # After a code is used, it becomes invalid/expired
        assert "Invalid or expired" in response_data.get("error", "")

        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestCompleteRegistration:
    """Test POST /register/complete endpoint."""

    async def test_complete_registration_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful registration completion."""
        # Create mock registration service
        mock_service = AsyncMock()
        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_test_key_123",
        )

        async def override_registration_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_registration_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
                "account_slug": "test-account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_id"] == str(mock_account.id)
        assert data["account_slug"] == "test-account"
        assert data["api_key"] == "ldr_test_key_123"

        app.dependency_overrides.clear()

    async def test_complete_registration_with_jam_code(self, client: AsyncClient):
        """Test registration with jam code."""
        mock_service = AsyncMock()
        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="test",
        )
        mock_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_test_key",
        )

        async def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
                "account_slug": "test-account",
                "jam_code": "GGJ2026",
            },
        )

        assert response.status_code == 201
        mock_service.complete_registration.assert_called_once()
        call_kwargs = mock_service.complete_registration.call_args.kwargs
        assert call_kwargs["jam_code"] == "GGJ2026"

        app.dependency_overrides.clear()

    async def test_complete_registration_invalid_token(self, client: AsyncClient):
        """Test registration with invalid verification token."""
        mock_service = AsyncMock()
        mock_service.complete_registration.side_effect = ValueError("Invalid token")

        async def override_service(*args, **kwargs):
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "invalid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 422

        app.dependency_overrides.clear()

    async def test_complete_registration_response_includes_display_name(self, client: AsyncClient):
        """Test that registration response includes user display_name."""
        mock_service = AsyncMock()
        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="john.doe@example.com",
            display_name="john.doe",
        )
        mock_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        async def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "display_name" in data
        assert data["display_name"] == "john.doe"

        app.dependency_overrides.clear()

    async def test_complete_registration_with_custom_display_name(self, client: AsyncClient):
        """Test registration with custom display_name."""
        mock_service = AsyncMock()
        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="test@example.com",
            display_name="My Custom Name",
        )
        mock_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        async def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
                "display_name": "My Custom Name",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "My Custom Name"

        # Verify service was called with display_name
        mock_service.complete_registration.assert_called_once()
        call_kwargs = mock_service.complete_registration.call_args.kwargs
        assert call_kwargs["display_name"] == "My Custom Name"

        app.dependency_overrides.clear()

    async def test_complete_registration_without_display_name(self, client: AsyncClient):
        """Test registration without display_name uses default."""
        mock_service = AsyncMock()
        mock_account = Account(
            id=AccountID(),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="jane@example.com",
            display_name="jane",  # Auto-generated from email
        )
        mock_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        async def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "jane"

        app.dependency_overrides.clear()

    async def test_complete_registration_duplicate_email(self, client: AsyncClient):
        """Test registration with already-registered email returns 409."""
        mock_service = AsyncMock()
        mock_service.complete_registration.side_effect = IntegrityError(
            statement="INSERT INTO users",
            params={},
            orig=Exception("duplicate key value violates unique constraint"),
        )

        async def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service

        response = await client.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "Email already registered"

        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestResendVerificationCode:
    """Test POST /register/resend-code endpoint."""

    async def test_resend_code_success(self, client: AsyncClient):
        """Test successful code resend."""
        response = await client.post(
            "/register/resend-code",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Verification code sent to email"

    async def test_resend_code_prevents_enumeration(self, client: AsyncClient):
        """Test that resend prevents email enumeration."""
        # Even if email doesn't exist, return success
        response = await client.post(
            "/register/resend-code",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestCreateJamCode:
    """Test POST /jam-codes endpoint (admin only)."""

    async def test_create_jam_code_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating jam code as superadmin."""
        # Mock auth context as superadmin
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()
        mock_auth.user_id = UserID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        response = await authenticated_client.post(
            "/jam-codes",
            json={
                "code": "SUMMER2024",
                "description": "Summer promotion",
                "features": {"discount": 20},
                "max_uses": 100,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "SUMMER2024"
        assert data["description"] == "Summer promotion"
        assert data["features"] == {"discount": 20}
        assert data["max_uses"] == 100

        app.dependency_overrides.clear()

    async def test_create_jam_code_non_superadmin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating jam code as non-superadmin fails."""
        mock_auth = Mock()
        mock_auth.is_superadmin = False
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        response = await authenticated_client.post(
            "/jam-codes",
            json={
                "code": "TEST",
                "description": "Test",
            },
        )

        assert response.status_code == 403
        assert "Superadmin access required" in response.json()["error"]

        app.dependency_overrides.clear()

    async def test_create_jam_code_duplicate(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating duplicate jam code fails."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()
        mock_auth.user_id = UserID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        # Create first code
        service = JamCodeService(db_session)
        await service.create_jam_code(code="DUPLICATE", description="Test")

        # Try to create duplicate
        response = await authenticated_client.post(
            "/jam-codes",
            json={
                "code": "DUPLICATE",
                "description": "Test",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestListJamCodes:
    """Test GET /jam-codes endpoint (admin only)."""

    async def test_list_jam_codes_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing jam codes as superadmin."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        # Create some codes
        service = JamCodeService(db_session)
        await service.create_jam_code(code="CODE1", description="First")
        await service.create_jam_code(code="CODE2", description="Second")

        response = await authenticated_client.get("/jam-codes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        app.dependency_overrides.clear()

    async def test_list_jam_codes_non_superadmin(self, authenticated_client: AsyncClient):
        """Test listing jam codes as non-superadmin fails."""
        mock_auth = Mock()
        mock_auth.is_superadmin = False
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        response = await authenticated_client.get("/jam-codes")

        assert response.status_code == 403

        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestGetJamCode:
    """Test GET /jam-codes/{id} endpoint (admin only)."""

    async def test_get_jam_code_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test getting specific jam code."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        # Create code
        service = JamCodeService(db_session)
        jam_code = await service.create_jam_code(code="GETME", description="Test")

        response = await authenticated_client.get(f"/jam-codes/{jam_code.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "GETME"

        app.dependency_overrides.clear()

    async def test_get_jam_code_not_found(self, authenticated_client: AsyncClient):
        """Test getting non-existent jam code."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        response = await authenticated_client.get(f"/jam-codes/{uuid4()}")

        assert response.status_code == 404

        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestUpdateJamCode:
    """Test PATCH /jam-codes/{id} endpoint (admin only)."""

    async def test_update_jam_code_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating jam code."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()
        mock_auth.user_id = UserID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        # Create code
        service = JamCodeService(db_session)
        jam_code = await service.create_jam_code(code="UPDATE", description="Original")

        response = await authenticated_client.patch(
            f"/jam-codes/{jam_code.id}",
            json={"description": "Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated"

        app.dependency_overrides.clear()

    async def test_update_jam_code_not_found(self, authenticated_client: AsyncClient):
        """Test updating non-existent jam code."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        response = await authenticated_client.patch(
            f"/jam-codes/{uuid4()}",
            json={"description": "Updated"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    async def test_update_jam_code_multiple_fields(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating multiple fields."""
        mock_auth = Mock()
        mock_auth.is_superadmin = True
        mock_auth.account_id = AccountID()
        mock_auth.user_id = UserID()

        async def override_auth():
            return mock_auth

        app.dependency_overrides[require_admin_auth] = override_auth

        service = JamCodeService(db_session)
        jam_code = await service.create_jam_code(code="MULTI", description="Original")

        response = await authenticated_client.patch(
            f"/jam-codes/{jam_code.id}",
            json={
                "description": "New description",
                "features": {"new": True},
                "max_uses": 50,
                "active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"
        assert data["features"] == {"new": True}
        assert data["max_uses"] == 50
        assert data["active"] is False

        app.dependency_overrides.clear()
