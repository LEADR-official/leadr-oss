"""Shared fixtures for board API tests."""

from unittest.mock import AsyncMock

import pytest

from leadr.auth.dependencies import (
    require_admin_auth,
    require_admin_auth_with_account_id,
    require_client_auth,
)
from leadr.boards.services.board_ratio_config_service import BoardRatioConfigService
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.boards.services.dependencies import (
    get_board_ratio_config_service,
    get_board_service,
    get_board_state_service,
    get_board_template_service,
    get_run_entry_service,
)
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.hooks import (
    get_post_create_board_hook,
    get_pre_create_board_hook,
    get_pre_create_board_template_hook,
    get_pre_update_board_template_hook,
    noop_post_create_board,
    noop_pre_create_board,
)
from leadr.games.services.dependencies import get_game_service
from leadr.games.services.game_service import GameService
from tests.conftest import make_admin_auth, make_client_auth


@pytest.fixture
def admin_auth(test_app):
    """Fixture for admin authentication context."""
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    test_app.dependency_overrides[require_admin_auth_with_account_id] = lambda: auth
    return auth


@pytest.fixture
def client_auth(test_app):
    """Fixture for client authentication context."""
    auth = make_client_auth()
    test_app.dependency_overrides[require_client_auth] = lambda: auth
    return auth


@pytest.fixture
def mock_board_service(test_app):
    """Fixture for mocked BoardService."""
    svc = AsyncMock(spec=BoardService)
    test_app.dependency_overrides[get_board_service] = lambda: svc
    return svc


@pytest.fixture
def mock_board_state_service(test_app):
    """Fixture for mocked BoardStateService."""
    svc = AsyncMock(spec=BoardStateService)
    test_app.dependency_overrides[get_board_state_service] = lambda: svc
    return svc


@pytest.fixture
def mock_board_template_service(test_app):
    """Fixture for mocked BoardTemplateService."""
    svc = AsyncMock(spec=BoardTemplateService)
    test_app.dependency_overrides[get_board_template_service] = lambda: svc
    return svc


@pytest.fixture
def mock_run_entry_service(test_app):
    """Fixture for mocked RunEntryService."""
    svc = AsyncMock(spec=RunEntryService)
    test_app.dependency_overrides[get_run_entry_service] = lambda: svc
    return svc


@pytest.fixture
def mock_board_ratio_config_service(test_app):
    """Fixture for mocked BoardRatioConfigService."""
    svc = AsyncMock(spec=BoardRatioConfigService)
    test_app.dependency_overrides[get_board_ratio_config_service] = lambda: svc
    return svc


@pytest.fixture
def mock_game_service(test_app):
    """Fixture for mocked GameService."""
    svc = AsyncMock(spec=GameService)
    test_app.dependency_overrides[get_game_service] = lambda: svc
    return svc


@pytest.fixture
def mock_board_hooks(test_app):
    """Fixture for mocked board hooks (pre/post create)."""
    test_app.dependency_overrides[get_pre_create_board_hook] = lambda: noop_pre_create_board
    test_app.dependency_overrides[get_post_create_board_hook] = lambda: noop_post_create_board
    return None


@pytest.fixture
def mock_board_template_hooks(test_app):
    """Fixture for mocked board template hooks."""
    test_app.dependency_overrides[get_pre_create_board_template_hook] = lambda: AsyncMock()
    test_app.dependency_overrides[get_pre_update_board_template_hook] = lambda: AsyncMock()
    return None
