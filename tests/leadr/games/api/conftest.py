"""Fixtures for isolated game API tests (no database)."""

from unittest.mock import AsyncMock

import pytest

from leadr.auth.dependencies import (
    require_admin_auth,
    require_admin_auth_with_account_id,
)
from leadr.common.api.hooks import (
    get_post_create_game_hook,
    get_pre_create_game_hook,
)
from leadr.common.domain.ids import AccountID
from leadr.games.services.dependencies import get_game_service
from leadr.games.services.game_service import GameService
from tests.conftest import make_admin_auth


@pytest.fixture
def admin_auth(test_app):
    """Create mock admin auth context and override auth dependencies."""
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    test_app.dependency_overrides[require_admin_auth_with_account_id] = lambda: auth
    return auth


@pytest.fixture
def mock_game_service(test_app):
    """Create mock game service and override dependency."""
    svc = AsyncMock(spec=GameService)
    test_app.dependency_overrides[get_game_service] = lambda: svc
    return svc


@pytest.fixture
def mock_hooks(test_app):
    """Create mock hooks and override hook dependencies."""
    pre_create = AsyncMock()
    post_create = AsyncMock()

    test_app.dependency_overrides[get_pre_create_game_hook] = lambda: pre_create
    test_app.dependency_overrides[get_post_create_game_hook] = lambda: post_create

    return {
        "pre_create": pre_create,
        "post_create": post_create,
    }


@pytest.fixture
def test_account_id() -> AccountID:
    """Generate a test account ID for use in tests."""
    return AccountID()
