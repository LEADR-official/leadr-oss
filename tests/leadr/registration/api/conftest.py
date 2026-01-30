"""Fixtures for registration API tests."""

from unittest.mock import AsyncMock

import pytest

from leadr.auth.dependencies import require_admin_auth
from leadr.registration.services.dependencies import (
    get_email_service,
    get_invite_service,
    get_jam_code_service,
    get_registration_service,
    get_verification_service,
)
from leadr.registration.services.invite_service import InviteService
from leadr.registration.services.jam_code_service import JamCodeService
from leadr.registration.services.registration_service import RegistrationService
from leadr.registration.services.verification_service import VerificationService
from tests.conftest import make_admin_auth


@pytest.fixture
def admin_auth(test_app):
    """Mock admin authentication context."""
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    return auth


@pytest.fixture
def mock_email_service(test_app):
    """Mock EmailService for registration tests."""
    svc = AsyncMock()
    test_app.dependency_overrides[get_email_service] = lambda: svc
    return svc


@pytest.fixture
def mock_verification_service(test_app):
    """Mock VerificationService for registration tests."""
    svc = AsyncMock(spec=VerificationService)
    test_app.dependency_overrides[get_verification_service] = lambda: svc
    return svc


@pytest.fixture
def mock_registration_service(test_app):
    """Mock RegistrationService for registration tests."""
    svc = AsyncMock(spec=RegistrationService)
    test_app.dependency_overrides[get_registration_service] = lambda: svc
    return svc


@pytest.fixture
def mock_invite_service(test_app):
    """Mock InviteService for registration tests."""
    svc = AsyncMock(spec=InviteService)
    test_app.dependency_overrides[get_invite_service] = lambda: svc
    return svc


@pytest.fixture
def mock_jam_code_service(test_app):
    """Mock JamCodeService for registration tests."""
    svc = AsyncMock(spec=JamCodeService)
    test_app.dependency_overrides[get_jam_code_service] = lambda: svc
    return svc
