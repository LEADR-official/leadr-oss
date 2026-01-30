"""Test fixtures for accounts API unit tests."""

from unittest.mock import AsyncMock

import pytest

from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.dependencies import get_account_service, get_user_service
from leadr.accounts.services.user_service import UserService
from leadr.auth.dependencies import (
    require_admin_auth,
    require_admin_auth_with_account_id,
    require_superadmin_auth,
)
from tests.conftest import make_admin_auth


@pytest.fixture
def admin_auth(test_app):
    """Mock admin auth context (superadmin by default)."""
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    test_app.dependency_overrides[require_admin_auth_with_account_id] = lambda: auth
    test_app.dependency_overrides[require_superadmin_auth] = lambda: auth
    return auth


@pytest.fixture
def mock_account_service(test_app):
    """Mock AccountService dependency."""
    svc = AsyncMock(spec=AccountService)
    test_app.dependency_overrides[get_account_service] = lambda: svc
    return svc


@pytest.fixture
def mock_user_service(test_app):
    """Mock UserService dependency."""
    svc = AsyncMock(spec=UserService)
    test_app.dependency_overrides[get_user_service] = lambda: svc
    return svc
