"""Tests for registration API routes."""

from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User, UserStatus
from leadr.auth.dependencies import require_admin_auth
from leadr.common.api.hooks import get_post_complete_registration_hook
from leadr.common.api.pagination import PaginatedResult
from leadr.common.domain.ids import AccountID, UserID
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.verification_code import VerificationCodeType
from tests.conftest import make_admin_auth


@pytest.mark.asyncio
class TestInitiateRegistration:
    """Test POST /register/initiate endpoint."""

    async def test_initiate_registration_success(
        self, mock_client_no_db, mock_verification_service
    ):
        """Test successful registration initiation."""
        response = await mock_client_no_db.post(
            "/register/initiate",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Verification code sent to email"
        assert data["code_expires_in"] == 600

        mock_verification_service.initiate_verification.assert_called_once_with("test@example.com")

    async def test_initiate_registration_invalid_email(
        self, mock_client_no_db, mock_verification_service
    ):
        """Test initiation with invalid email format."""
        response = await mock_client_no_db.post(
            "/register/initiate",
            json={"email": "not-an-email"},
        )

        # Pydantic validates email format and returns 422
        assert response.status_code == 422

    async def test_initiate_registration_prevents_enumeration(
        self, mock_client_no_db, mock_verification_service
    ):
        """Test that errors don't reveal if email exists."""
        # Even if service fails, should return success to prevent enumeration
        mock_verification_service.initiate_verification.side_effect = Exception("Some error")

        response = await mock_client_no_db.post(
            "/register/initiate",
            json={"email": "any@example.com"},
        )

        assert response.status_code == 201


@pytest.mark.asyncio
class TestVerifyCode:
    """Test POST /register/verify endpoint."""

    async def test_verify_code_success(self, mock_client_no_db, mock_verification_service):
        """Test successful code verification."""
        mock_verification_service.verify_code.return_value = (
            "mock_verification_token",
            VerificationCodeType.REGISTRATION,
        )

        response = await mock_client_no_db.post(
            "/register/verify",
            json={"email": "test@example.com", "code": "ABC123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verification_token" in data
        assert data["expires_in"] == 600
        assert data["type"] == "registration"

        mock_verification_service.verify_code.assert_called_once_with("test@example.com", "ABC123")

    async def test_verify_code_invalid(self, mock_client_no_db, mock_verification_service):
        """Test verifying invalid code."""
        # Code must be exactly 6 alphanumeric characters
        response = await mock_client_no_db.post(
            "/register/verify",
            json={"email": "test@example.com", "code": "WRONG"},
        )

        # Pydantic validates code format and returns 422
        assert response.status_code == 422

    async def test_verify_code_already_used(self, mock_client_no_db, mock_verification_service):
        """Test verifying already-used code."""
        mock_verification_service.verify_code.side_effect = ValueError(
            "Invalid or expired verification code"
        )

        response = await mock_client_no_db.post(
            "/register/verify",
            json={"email": "test@example.com", "code": "ABC123"},
        )

        assert response.status_code == 400
        response_data = response.json()
        assert "Invalid or expired" in response_data.get("error", "")

    async def test_verify_invite_code_returns_invite_type(
        self, mock_client_no_db, mock_verification_service
    ):
        """Test that verifying an invite code returns INVITE type."""
        mock_verification_service.verify_code.return_value = (
            "mock_verification_token",
            VerificationCodeType.INVITE,
        )

        response = await mock_client_no_db.post(
            "/register/verify",
            json={"email": "invited@example.com", "code": "INV123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verification_token" in data
        assert data["type"] == "invite"


@pytest.mark.asyncio
class TestCompleteRegistration:
    """Test POST /register/complete endpoint."""

    async def test_complete_registration_success(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test successful registration completion."""
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
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_test_key_123",
        )

        response = await mock_client_no_db.post(
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

    async def test_complete_registration_with_jam_code(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test registration with jam code."""
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
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_test_key",
        )

        response = await mock_client_no_db.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
                "account_slug": "test-account",
                "jam_code": "GGJ2026",
            },
        )

        assert response.status_code == 201
        mock_registration_service.complete_registration.assert_called_once()
        call_kwargs = mock_registration_service.complete_registration.call_args.kwargs
        assert call_kwargs["jam_code"] == "GGJ2026"

    async def test_complete_registration_invalid_token(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test registration with invalid verification token."""
        mock_registration_service.complete_registration.side_effect = ValueError("Invalid token")

        response = await mock_client_no_db.post(
            "/register/complete",
            json={
                "verification_token": "invalid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 400

    async def test_complete_registration_response_includes_display_name(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test that registration response includes user display_name."""
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
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        response = await mock_client_no_db.post(
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

    async def test_complete_registration_with_custom_display_name(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test registration with custom display_name."""
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
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        response = await mock_client_no_db.post(
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
        mock_registration_service.complete_registration.assert_called_once()
        call_kwargs = mock_registration_service.complete_registration.call_args.kwargs
        assert call_kwargs["display_name"] == "My Custom Name"

    async def test_complete_registration_without_display_name(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test registration without display_name uses default."""
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
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        response = await mock_client_no_db.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "jane"

    async def test_complete_registration_duplicate_email(
        self, mock_client_no_db, mock_registration_service
    ):
        """Test registration with already-registered email returns 409."""
        mock_registration_service.complete_registration.side_effect = IntegrityError(
            statement="INSERT INTO users",
            params={},
            orig=Exception("duplicate key value violates unique constraint"),
        )

        response = await mock_client_no_db.post(
            "/register/complete",
            json={
                "verification_token": "valid_token",
                "account_name": "Test Account",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "Email already registered"

    async def test_post_hook_called_with_registration_data(
        self, test_app, mock_client_no_db, mock_registration_service
    ):
        """Post hook should be called with the created account and user data."""
        mock_account = Account(
            id=AccountID(),
            name="Hook Test Account",
            slug="hook-test",
            status=AccountStatus.ACTIVE,
        )
        mock_user = User(
            id=UserID(),
            account_id=mock_account.id,
            email="hook@example.com",
            display_name="hookuser",
        )
        mock_registration_service.complete_registration.return_value = (
            mock_account,
            mock_user,
            "ldr_key",
        )

        mock_hook = AsyncMock()
        test_app.dependency_overrides[get_post_complete_registration_hook] = lambda: mock_hook

        response = await mock_client_no_db.post(
            "/register/complete",
            json={"verification_token": "valid_token", "account_name": "Hook Test Account"},
        )

        assert response.status_code == 201
        mock_hook.assert_called_once_with(
            email="hook@example.com",
            display_name="hookuser",
            account_name="Hook Test Account",
            account_slug="hook-test",
            background_tasks=ANY,
        )

    async def test_post_hook_not_called_on_error(
        self, test_app, mock_client_no_db, mock_registration_service
    ):
        """Post hook should NOT be called when registration fails."""
        mock_registration_service.complete_registration.side_effect = ValueError("Invalid token")

        mock_hook = AsyncMock()
        test_app.dependency_overrides[get_post_complete_registration_hook] = lambda: mock_hook

        response = await mock_client_no_db.post(
            "/register/complete",
            json={"verification_token": "bad_token", "account_name": "Test"},
        )

        assert response.status_code == 400
        mock_hook.assert_not_called()


@pytest.mark.asyncio
class TestResendVerificationCode:
    """Test POST /register/resend-code endpoint."""

    async def test_resend_code_success(self, mock_client_no_db, mock_verification_service):
        """Test successful code resend."""
        response = await mock_client_no_db.post(
            "/register/resend-code",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Verification code sent to email"

    async def test_resend_code_prevents_enumeration(
        self, mock_client_no_db, mock_verification_service
    ):
        """Test that resend prevents email enumeration."""
        # Even if email doesn't exist, return success
        mock_verification_service.initiate_verification.side_effect = Exception("Error")

        response = await mock_client_no_db.post(
            "/register/resend-code",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestInviteUser:
    """Test POST /register/invite endpoint (admin only)."""

    async def test_invite_user_success(self, mock_client_no_db, admin_auth, mock_invite_service):
        """Test successful user invite by admin."""
        mock_user = User(
            id=UserID(),
            account_id=admin_auth.account_id,
            email="invited@example.com",
            display_name="invited",
            status=UserStatus.INVITED,
        )
        mock_invite_service.send_invite.return_value = mock_user

        response = await mock_client_no_db.post(
            "/register/invite",
            json={
                "email": "invited@example.com",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "invited@example.com"
        assert data["status"] == "invited"
        assert "user_id" in data
        assert "message" in data

        # Verify service was called with auth.account_id
        mock_invite_service.send_invite.assert_called_once_with(
            email="invited@example.com",
            account_id=admin_auth.account_id,
            display_name=None,
        )

    async def test_invite_user_with_display_name(
        self, mock_client_no_db, admin_auth, mock_invite_service
    ):
        """Test user invite with custom display name."""
        mock_user = User(
            id=UserID(),
            account_id=admin_auth.account_id,
            email="invited@example.com",
            display_name="Custom Name",
            status=UserStatus.INVITED,
        )
        mock_invite_service.send_invite.return_value = mock_user

        response = await mock_client_no_db.post(
            "/register/invite",
            json={
                "email": "invited@example.com",
                "display_name": "Custom Name",
            },
        )

        assert response.status_code == 201
        mock_invite_service.send_invite.assert_called_once_with(
            email="invited@example.com",
            account_id=admin_auth.account_id,
            display_name="Custom Name",
        )

    async def test_invite_user_already_active(
        self, mock_client_no_db, admin_auth, mock_invite_service
    ):
        """Test inviting already-active user returns error."""
        mock_invite_service.send_invite.side_effect = ValueError(
            "User with email already exists and is active"
        )

        response = await mock_client_no_db.post(
            "/register/invite",
            json={
                "email": "active@example.com",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

    async def test_invite_user_invalid_email(
        self, mock_client_no_db, admin_auth, mock_invite_service
    ):
        """Test invite with invalid email format."""
        response = await mock_client_no_db.post(
            "/register/invite",
            json={
                "email": "not-an-email",
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestCreateJamCode:
    """Test POST /jam-codes endpoint (admin only)."""

    async def test_create_jam_code_success(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test creating jam code as superadmin."""
        mock_jam_code = JamCode(
            code="SUMMER2024",
            description="Summer promotion",
            features={"discount": 20},
            max_uses=100,
        )
        mock_jam_code_service.create_jam_code.return_value = mock_jam_code

        response = await mock_client_no_db.post(
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

    async def test_create_jam_code_non_superadmin(
        self, mock_client_no_db, test_app, mock_jam_code_service
    ):
        """Test creating jam code as non-superadmin fails."""
        # Override with non-superadmin auth
        non_superadmin_auth = make_admin_auth(is_superadmin=False)
        test_app.dependency_overrides[require_admin_auth] = lambda: non_superadmin_auth

        response = await mock_client_no_db.post(
            "/jam-codes",
            json={
                "code": "TEST",
                "description": "Test",
            },
        )

        assert response.status_code == 403
        assert "Superadmin access required" in response.json()["error"]

    async def test_create_jam_code_duplicate(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test creating duplicate jam code fails."""
        mock_jam_code_service.create_jam_code.side_effect = ValueError("Jam code already exists")

        response = await mock_client_no_db.post(
            "/jam-codes",
            json={
                "code": "DUPLICATE",
                "description": "Test",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["error"]


@pytest.mark.asyncio
class TestListJamCodes:
    """Test GET /jam-codes endpoint (admin only)."""

    async def test_list_jam_codes_success(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test listing jam codes as superadmin."""
        mock_codes = [
            JamCode(code="CODE1", description="First"),
            JamCode(code="CODE2", description="Second"),
        ]
        mock_result = PaginatedResult(
            items=mock_codes,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_jam_code_service.list_jam_codes.return_value = mock_result

        response = await mock_client_no_db.get("/jam-codes")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    async def test_list_jam_codes_non_superadmin(
        self, mock_client_no_db, test_app, mock_jam_code_service
    ):
        """Test listing jam codes as non-superadmin fails."""
        non_superadmin_auth = make_admin_auth(is_superadmin=False)
        test_app.dependency_overrides[require_admin_auth] = lambda: non_superadmin_auth

        response = await mock_client_no_db.get("/jam-codes")

        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetJamCode:
    """Test GET /jam-codes/{id} endpoint (admin only)."""

    async def test_get_jam_code_success(self, mock_client_no_db, admin_auth, mock_jam_code_service):
        """Test getting specific jam code."""
        jam_code_id = uuid4()
        mock_jam_code = JamCode(code="GETME", description="Test")
        mock_jam_code_service.get_jam_code_by_id.return_value = mock_jam_code

        response = await mock_client_no_db.get(f"/jam-codes/{jam_code_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "GETME"

    async def test_get_jam_code_not_found(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test getting non-existent jam code."""
        mock_jam_code_service.get_jam_code_by_id.return_value = None

        response = await mock_client_no_db.get(f"/jam-codes/{uuid4()}")

        assert response.status_code == 404

    async def test_get_jam_code_non_superadmin(
        self, mock_client_no_db, test_app, mock_jam_code_service
    ):
        """Test getting jam code as non-superadmin fails."""
        non_superadmin_auth = make_admin_auth(is_superadmin=False)
        test_app.dependency_overrides[require_admin_auth] = lambda: non_superadmin_auth

        response = await mock_client_no_db.get(f"/jam-codes/{uuid4()}")

        assert response.status_code == 403
        assert "Superadmin access required" in response.json()["error"]


@pytest.mark.asyncio
class TestUpdateJamCode:
    """Test PATCH /jam-codes/{id} endpoint (admin only)."""

    async def test_update_jam_code_success(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test updating jam code."""
        jam_code_id = uuid4()
        mock_jam_code = JamCode(code="UPDATE", description="Updated")
        mock_jam_code_service.update_jam_code.return_value = mock_jam_code

        response = await mock_client_no_db.patch(
            f"/jam-codes/{jam_code_id}",
            json={"description": "Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated"

    async def test_update_jam_code_not_found(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test updating non-existent jam code."""
        mock_jam_code_service.update_jam_code.side_effect = ValueError("Jam code not found")

        response = await mock_client_no_db.patch(
            f"/jam-codes/{uuid4()}",
            json={"description": "Updated"},
        )

        assert response.status_code == 404

    async def test_update_jam_code_multiple_fields(
        self, mock_client_no_db, admin_auth, mock_jam_code_service
    ):
        """Test updating multiple fields."""
        jam_code_id = uuid4()
        mock_jam_code = JamCode(
            code="MULTI",
            description="New description",
            features={"new": True},
            max_uses=50,
            active=False,
        )
        mock_jam_code_service.update_jam_code.return_value = mock_jam_code

        response = await mock_client_no_db.patch(
            f"/jam-codes/{jam_code_id}",
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

    async def test_update_jam_code_non_superadmin(
        self, mock_client_no_db, test_app, mock_jam_code_service
    ):
        """Test updating jam code as non-superadmin fails."""
        non_superadmin_auth = make_admin_auth(is_superadmin=False)
        test_app.dependency_overrides[require_admin_auth] = lambda: non_superadmin_auth

        response = await mock_client_no_db.patch(
            f"/jam-codes/{uuid4()}",
            json={"description": "Updated"},
        )

        assert response.status_code == 403
        assert "Superadmin access required" in response.json()["error"]
