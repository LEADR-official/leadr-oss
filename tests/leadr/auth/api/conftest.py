"""Fixtures for auth API tests (isolated unit tests with mocked services)."""

from unittest.mock import AsyncMock

import pytest

from leadr.auth.dependencies import (
    require_admin_auth,
    require_admin_auth_with_account_id,
    require_client_auth,
    require_client_auth_with_nonce,
)
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.dependencies import (
    get_api_key_service,
    get_device_service,
    get_identity_service,
    get_nonce_service,
)
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.auth.services.nonce_service import NonceService
from tests.conftest import make_admin_auth, make_client_auth


@pytest.fixture
def admin_auth(test_app):
    """Mock admin authentication context for admin routes.

    Provides a superadmin auth context by default.
    Routes using require_admin_auth or require_admin_auth_with_account_id will receive this.
    """
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    test_app.dependency_overrides[require_admin_auth_with_account_id] = lambda: auth
    return auth


@pytest.fixture
def client_auth(test_app):
    """Mock client authentication context for client routes.

    Routes using require_client_auth or require_client_auth_with_nonce will receive this.
    """
    auth = make_client_auth()
    test_app.dependency_overrides[require_client_auth] = lambda: auth
    test_app.dependency_overrides[require_client_auth_with_nonce] = lambda: auth
    return auth


@pytest.fixture
def mock_api_key_service(test_app):
    """Mock APIKeyService for isolated unit tests."""
    svc = AsyncMock(spec=APIKeyService)
    test_app.dependency_overrides[get_api_key_service] = lambda: svc
    return svc


@pytest.fixture
def mock_device_service(test_app):
    """Mock DeviceService for isolated unit tests."""
    svc = AsyncMock(spec=DeviceService)
    test_app.dependency_overrides[get_device_service] = lambda: svc
    return svc


@pytest.fixture
def mock_identity_service(test_app):
    """Mock IdentityService for isolated unit tests."""
    svc = AsyncMock(spec=IdentityService)
    test_app.dependency_overrides[get_identity_service] = lambda: svc
    return svc


@pytest.fixture
def mock_nonce_service(test_app):
    """Mock NonceService for isolated unit tests."""
    svc = AsyncMock(spec=NonceService)
    test_app.dependency_overrides[get_nonce_service] = lambda: svc
    return svc
