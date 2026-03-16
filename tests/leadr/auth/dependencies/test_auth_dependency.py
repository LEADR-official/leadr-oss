"""Tests for AuthContextDependency class."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from starlette.datastructures import State

from leadr.auth.dependencies import AuthContextDependency
from leadr.common.domain.ids import AccountID, GameID


@pytest.mark.asyncio
class TestAuthContextDependencyInit:
    """Test suite for AuthContextDependency initialization."""

    async def test_init_requires_at_least_one_auth_type(self):
        """Test that __init__ raises ValueError when neither auth type is required."""
        with pytest.raises(
            ValueError, match="At least one of require_admin or require_client must be True"
        ):
            AuthContextDependency(require_admin=False, require_client=False)

    async def test_init_allows_admin_only(self):
        """Test that __init__ allows admin-only auth."""
        dep = AuthContextDependency(require_admin=True, require_client=False)
        assert dep.require_admin is True
        assert dep.require_client is False
        assert dep.require_nonce is False

    async def test_init_allows_client_only(self):
        """Test that __init__ allows client-only auth."""
        dep = AuthContextDependency(require_admin=False, require_client=True)
        assert dep.require_admin is False
        assert dep.require_client is True
        assert dep.require_nonce is False

    async def test_init_allows_both_auth_types(self):
        """Test that __init__ allows both auth types (OR logic)."""
        dep = AuthContextDependency(require_admin=True, require_client=True)
        assert dep.require_admin is True
        assert dep.require_client is True
        assert dep.require_nonce is False

    async def test_init_allows_client_with_nonce(self):
        """Test that __init__ allows client auth with nonce requirement."""
        dep = AuthContextDependency(require_admin=False, require_client=True, require_nonce=True)
        assert dep.require_admin is False
        assert dep.require_client is True
        assert dep.require_nonce is True

    async def test_admin_auth_sets_account_id_on_request_state(self):
        """Test that successful admin auth sets account_id on request.state."""
        dep = AuthContextDependency(require_admin=True)

        account_id = AccountID(uuid4())
        mock_key = Mock()
        mock_key.account_id = account_id
        mock_user = Mock()

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.state = State()

        mock_api_key_service = AsyncMock()
        mock_api_key_service.validate_api_key_with_user.return_value = (mock_key, mock_user)
        mock_api_key_service.should_update_usage.return_value = False

        await dep(
            request=mock_request,
            api_key_service=mock_api_key_service,
            user_service=AsyncMock(),
            identity_service=AsyncMock(),
            nonce_service=AsyncMock(),
            background_tasks=BackgroundTasks(),
            api_key="ldr_test",
            authorization=None,
            leadr_client_nonce=None,
        )

        assert mock_request.state.account_id == str(account_id)
        assert not hasattr(mock_request.state, "game_id")

    async def test_client_auth_sets_account_id_and_game_id_on_request_state(self):
        """Test that successful client auth sets account_id and game_id on request.state."""
        dep = AuthContextDependency(require_client=True)

        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        mock_identity = Mock()
        mock_identity.account_id = account_id
        mock_identity.game_id = game_id

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.state = State()

        mock_identity_service = AsyncMock()
        mock_identity_service.validate_identity_token.return_value = mock_identity

        with patch("leadr.auth.dependencies.validate_access_token", return_value={}):
            await dep(
                request=mock_request,
                api_key_service=AsyncMock(),
                user_service=AsyncMock(),
                identity_service=mock_identity_service,
                nonce_service=AsyncMock(),
                background_tasks=BackgroundTasks(),
                api_key=None,
                authorization="Bearer some.jwt.token",
                leadr_client_nonce=None,
            )

        assert mock_request.state.account_id == str(account_id)
        assert mock_request.state.game_id == str(game_id)

    async def test_unreachable_fallback_raises_value_error(self):
        """Test the safety fallback ValueError that should never be reached."""
        # Create instance with valid config
        dep = AuthContextDependency(require_admin=True, require_client=False)

        # Bypass validation by directly setting invalid state
        dep.require_admin = False
        dep.require_client = False

        # Mock all dependencies
        mock_request = Mock()
        mock_api_key_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_identity_service = AsyncMock()
        mock_nonce_service = AsyncMock()
        background_tasks = BackgroundTasks()

        # This should hit the safety fallback
        with pytest.raises(
            ValueError, match="At least one of require_admin or require_client must be True"
        ):
            await dep(
                request=mock_request,
                api_key_service=mock_api_key_service,
                user_service=mock_user_service,
                identity_service=mock_identity_service,
                nonce_service=mock_nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization=None,
                leadr_client_nonce=None,
            )
