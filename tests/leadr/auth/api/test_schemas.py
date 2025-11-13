"""Tests for API Key API schemas."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.auth.api.schemas import (
    APIKeyResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    UpdateAPIKeyRequest,
)
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.common.domain.ids import AccountID, APIKeyID, UserID


class TestCreateAPIKeyRequest:
    """Test suite for CreateAPIKeyRequest schema."""

    def test_create_request_with_all_fields(self):
        """Test creating request with all fields."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        expires_at = datetime.now(UTC) + timedelta(days=90)

        request = CreateAPIKeyRequest(
            account_id=account_id,
            user_id=user_id,
            name="Production Key",
            expires_at=expires_at,
        )

        assert request.account_id == account_id
        assert request.user_id == user_id
        assert request.name == "Production Key"
        assert request.expires_at == expires_at

    def test_create_request_without_expiration(self):
        """Test creating request without expiration."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        request = CreateAPIKeyRequest(
            account_id=account_id,
            user_id=user_id,
            name="Production Key",
        )

        assert request.account_id == account_id
        assert request.user_id == user_id
        assert request.name == "Production Key"
        assert request.expires_at is None

    def test_create_request_requires_account_id(self):
        """Test that account_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAPIKeyRequest(  # type: ignore[call-arg]
                name="Production Key",
            )

        assert "account_id" in str(exc_info.value)

    def test_create_request_requires_name(self):
        """Test that name is required."""
        account_id = AccountID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            CreateAPIKeyRequest(  # type: ignore[call-arg]
                account_id=account_id,
            )

        assert "name" in str(exc_info.value)


class TestCreateAPIKeyResponse:
    """Test suite for CreateAPIKeyResponse schema."""

    def test_create_response_with_all_fields(self):
        """Test creating response with all fields."""
        key_id = APIKeyID(uuid4())
        expires_at = datetime.now(UTC) + timedelta(days=90)
        created_at = datetime.now(UTC)

        response = CreateAPIKeyResponse(
            id=key_id,
            name="Production Key",
            key="ldr_test123456789012345678901234",
            prefix="ldr_test123456",
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at,
            created_at=created_at,
        )

        assert response.id == key_id
        assert response.name == "Production Key"
        assert response.key == "ldr_test123456789012345678901234"
        assert response.prefix == "ldr_test123456"
        assert response.status == APIKeyStatus.ACTIVE
        assert response.expires_at == expires_at
        assert response.created_at == created_at

    def test_create_response_without_expiration(self):
        """Test creating response without expiration."""
        key_id = APIKeyID(uuid4())
        created_at = datetime.now(UTC)

        response = CreateAPIKeyResponse(
            id=key_id,
            name="Production Key",
            key="ldr_test123456789012345678901234",
            prefix="ldr_test123456",
            status=APIKeyStatus.ACTIVE,
            created_at=created_at,
        )

        assert response.expires_at is None

    def test_create_response_requires_key(self):
        """Test that key field is required in create response."""
        key_id = APIKeyID(uuid4())
        created_at = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            CreateAPIKeyResponse(  # type: ignore[call-arg]
                id=key_id,
                name="Production Key",
                prefix="ldr_test123456",
                status=APIKeyStatus.ACTIVE,
                created_at=created_at,
            )

        assert "key" in str(exc_info.value)


class TestAPIKeyResponse:
    """Test suite for APIKeyResponse schema."""

    def test_api_key_response_with_all_fields(self):
        """Test creating response with all fields."""
        key_id = APIKeyID(uuid4())
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        last_used_at = datetime.now(UTC) - timedelta(hours=1)
        expires_at = datetime.now(UTC) + timedelta(days=90)
        created_at = datetime.now(UTC) - timedelta(days=30)
        updated_at = datetime.now(UTC)

        response = APIKeyResponse(
            id=key_id,
            account_id=account_id,
            user_id=user_id,
            name="Production Key",
            prefix="ldr_test123456",
            status=APIKeyStatus.ACTIVE,
            last_used_at=last_used_at,
            expires_at=expires_at,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert response.id == key_id
        assert response.account_id == account_id
        assert response.user_id == user_id
        assert response.name == "Production Key"
        assert response.prefix == "ldr_test123456"
        assert response.status == APIKeyStatus.ACTIVE
        assert response.last_used_at == last_used_at
        assert response.expires_at == expires_at
        assert response.created_at == created_at
        assert response.updated_at == updated_at

    def test_api_key_response_without_optional_fields(self):
        """Test creating response without optional fields."""
        key_id = APIKeyID(uuid4())
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        response = APIKeyResponse(
            id=key_id,
            account_id=account_id,
            user_id=user_id,
            name="Production Key",
            prefix="ldr_test123456",
            status=APIKeyStatus.ACTIVE,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert response.last_used_at is None
        assert response.expires_at is None

    def test_api_key_response_does_not_include_key_hash(self):
        """Test that APIKeyResponse does not have key_hash field."""
        key_id = APIKeyID(uuid4())
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        # Should not be able to set key_hash due to extra="forbid"
        with pytest.raises(ValidationError):
            data = {
                "id": key_id,
                "account_id": account_id,
                "user_id": user_id,
                "name": "Production Key",
                "prefix": "ldr_test123456",
                "status": APIKeyStatus.ACTIVE,
                "key_hash": "should_not_work",
                "created_at": created_at,
                "updated_at": updated_at,
            }
            APIKeyResponse(**data)


class TestUpdateAPIKeyRequest:
    """Test suite for UpdateAPIKeyRequest schema."""

    def test_update_request_with_status(self):
        """Test updating status."""
        request = UpdateAPIKeyRequest(status=APIKeyStatus.REVOKED)

        assert request.status == APIKeyStatus.REVOKED
        assert request.deleted is None

    def test_update_request_with_deleted(self):
        """Test soft delete flag."""
        request = UpdateAPIKeyRequest(deleted=True)

        assert request.status is None
        assert request.deleted is True

    def test_update_request_with_both_fields(self):
        """Test updating both status and deleted."""
        request = UpdateAPIKeyRequest(
            status=APIKeyStatus.REVOKED,
            deleted=True,
        )

        assert request.status == APIKeyStatus.REVOKED
        assert request.deleted is True

    def test_update_request_with_no_fields(self):
        """Test that at least one field is accepted (validation in endpoint)."""
        request = UpdateAPIKeyRequest()

        assert request.status is None
        assert request.deleted is None

    def test_update_request_defaults_to_none(self):
        """Test that fields default to None."""
        request = UpdateAPIKeyRequest()

        assert request.status is None
        assert request.deleted is None
