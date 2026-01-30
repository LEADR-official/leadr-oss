"""Tests for API Key API routes - unit tests with mocked services."""

import pytest
from httpx import AsyncClient

from leadr.auth.domain.api_key import APIKey
from leadr.common.api.pagination import PaginatedResult
from leadr.common.domain.ids import AccountID, APIKeyID, UserID


@pytest.mark.asyncio
class TestSuperadminOptionalAccountId:
    """Test suite for superadmin optional account_id on list endpoints."""

    async def test_superadmin_list_api_keys_without_account_id_returns_all(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ):
        """Test that superadmin can list API keys WITHOUT account_id and sees all accounts."""
        # Create mock API keys from two accounts
        account1_id = AccountID()
        account2_id = AccountID()

        api_key1 = APIKey(
            id=APIKeyID(),
            account_id=account1_id,
            user_id=UserID(),
            name="Account 1 Key",
            key_hash="hash1",
            key_prefix="ldr_test1",
        )
        api_key2 = APIKey(
            id=APIKeyID(),
            account_id=account2_id,
            user_id=UserID(),
            name="Account 2 Key",
            key_hash="hash2",
            key_prefix="ldr_test2",
        )

        # Mock service to return both keys
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=[api_key1, api_key2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # List API keys WITHOUT account_id - should return keys from ALL accounts
        response = await mock_client_no_db.get("/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain API keys from both accounts
        key_names = {k["name"] for k in data["data"]}
        assert "Account 1 Key" in key_names
        assert "Account 2 Key" in key_names

        # Verify service was called with account_id=None (superadmin sees all)
        mock_api_key_service.list_api_keys.assert_called_once()
        call_kwargs = mock_api_key_service.list_api_keys.call_args.kwargs
        assert call_kwargs["account_id"] is None
