"""Tests for Client Authentication API routes."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestClientSessionRoutes:
    """Test suite for client session API routes."""

    async def test_start_session_creates_new_device(self, client: AsyncClient, db_session):
        """Test starting a session creates a new device and returns token."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session
        device_id = str(uuid4())
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "ios",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == device_id
        assert data["game_id"] == str(game.id)
        assert data["platform"] == "ios"
        assert "access_token" in data
        assert "expires_in" in data
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 50  # JWT tokens are long

    async def test_start_session_updates_existing_device(self, client: AsyncClient, db_session):
        """Test starting a session for existing device updates last_seen_at."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start first session
        device_id = str(uuid4())
        response1 = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "android",
            },
        )
        assert response1.status_code == 201
        device_id_from_first = response1.json()["id"]

        # Start second session with same device_id
        response2 = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "android",
            },
        )

        assert response2.status_code == 201
        data = response2.json()
        # Should be same device entity
        assert data["id"] == device_id_from_first
        assert data["device_id"] == device_id
        # But new access token
        assert data["access_token"] != response1.json()["access_token"]

    async def test_start_session_with_metadata(self, client: AsyncClient, db_session):
        """Test starting a session with device metadata."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session with metadata
        device_id = str(uuid4())
        metadata = {
            "device_model": "iPhone 14 Pro",
            "os_version": "iOS 17.2",
            "app_version": "1.2.3",
        }
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "ios",
                "metadata": metadata,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == metadata

    async def test_start_session_without_platform(self, client: AsyncClient, db_session):
        """Test starting a session without platform (optional field)."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session without platform
        device_id = str(uuid4())
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == device_id
        assert data["platform"] is None

    async def test_start_session_with_nonexistent_game_returns_404(self, client: AsyncClient):
        """Test starting a session with nonexistent game returns 404."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": "00000000-0000-0000-0000-000000000000",
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 404
        assert "game" in response.json()["detail"].lower()

    async def test_start_session_requires_game_id(self, client: AsyncClient):
        """Test starting a session without game_id returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 422

    async def test_start_session_requires_device_id(self, client: AsyncClient):
        """Test starting a session without device_id returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(uuid4()),
            },
        )

        assert response.status_code == 422

    async def test_start_session_with_invalid_game_id_format_returns_422(self, client: AsyncClient):
        """Test starting a session with invalid game_id format returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": "not-a-uuid",
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestClientNonceRoutes:
    """Test suite for client nonce API routes."""

    async def test_generate_nonce_success(self, client: AsyncClient, db_session):
        """Test generating a nonce with valid device token."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session to get device token
        device_id = str(uuid4())
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Generate nonce
        response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "nonce_value" in data
        assert "expires_at" in data
        assert len(data["nonce_value"]) == 36  # UUID string length

    async def test_generate_nonce_without_auth_returns_401(self, client: AsyncClient):
        """Test generating a nonce without authentication returns 401."""
        response = await client.get("/client/nonce")

        assert response.status_code == 401
        assert "required" in response.json()["detail"].lower()

    async def test_generate_nonce_with_invalid_token_returns_401(self, client: AsyncClient):
        """Test generating a nonce with invalid token returns 401."""
        response = await client.get(
            "/client/nonce",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_generate_multiple_nonces_for_same_device(self, client: AsyncClient, db_session):
        """Test that a device can generate multiple nonces."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session
        device_id = str(uuid4())
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
            },
        )
        access_token = session_response.json()["access_token"]

        # Generate first nonce
        response1 = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response1.status_code == 200
        nonce1 = response1.json()["nonce_value"]

        # Generate second nonce
        response2 = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response2.status_code == 200
        nonce2 = response2.json()["nonce_value"]

        # Nonces should be different
        assert nonce1 != nonce2


@pytest.mark.asyncio
class TestNonceIntegration:
    """Integration tests for full nonce flow."""

    async def test_full_nonce_flow(self, client: AsyncClient, db_session):
        """Test complete nonce flow: session → nonce generation → validation → consumption."""
        from leadr.auth.services.nonce_service import NonceService

        # 1. Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # 2. Start device session
        device_id = str(uuid4())
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # 3. Generate nonce for the device
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce_data = nonce_response.json()
        nonce_value = nonce_data["nonce_value"]
        expires_at = nonce_data["expires_at"]

        # Verify nonce properties
        assert nonce_value is not None
        assert expires_at is not None

        # 4. Verify nonce is valid and can be consumed
        nonce_service = NonceService(db_session)
        device_service = DeviceService(db_session)

        # Get device entity
        device = await device_service.repository.get_by_game_and_device_id(game.id, device_id)
        assert device is not None

        # Validate and consume the nonce
        result = await nonce_service.validate_and_consume_nonce(nonce_value, device.id)
        assert result is True

        # 5. Verify nonce cannot be reused (should raise ValueError)
        with pytest.raises(ValueError, match="already used"):
            await nonce_service.validate_and_consume_nonce(nonce_value, device.id)

        # 6. Generate new nonce and verify it works
        nonce_response2 = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response2.status_code == 200
        nonce_value2 = nonce_response2.json()["nonce_value"]

        # New nonce should be different
        assert nonce_value2 != nonce_value

        # New nonce should be valid
        result2 = await nonce_service.validate_and_consume_nonce(nonce_value2, device.id)
        assert result2 is True

    async def test_nonce_cannot_be_used_by_different_device(self, client: AsyncClient, db_session):
        """Test that a nonce generated for one device cannot be used by another."""
        from leadr.auth.services.nonce_service import NonceService

        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start sessions for two devices
        device1_id = str(uuid4())
        device2_id = str(uuid4())

        session1 = await client.post(
            "/client/sessions",
            json={"game_id": str(game.id), "device_id": device1_id},
        )
        access_token1 = session1.json()["access_token"]

        # Start session for device 2
        await client.post(
            "/client/sessions",
            json={"game_id": str(game.id), "device_id": device2_id},
        )

        # Generate nonce for device 1
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token1}"},
        )
        nonce_value = nonce_response.json()["nonce_value"]

        # Try to use device1's nonce with device2
        device_service = DeviceService(db_session)
        device2 = await device_service.repository.get_by_game_and_device_id(game.id, device2_id)
        assert device2 is not None

        nonce_service = NonceService(db_session)
        with pytest.raises(ValueError, match="does not belong"):
            await nonce_service.validate_and_consume_nonce(nonce_value, device2.id)

    async def test_expired_nonce_cannot_be_used(self, client: AsyncClient, db_session):
        """Test that an expired nonce cannot be used."""
        from datetime import UTC, datetime, timedelta

        from leadr.auth.adapters.orm import NonceORM
        from leadr.auth.services.nonce_service import NonceService

        # Create account, game, and device
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Get device via session
        device_id = str(uuid4())
        await client.post(
            "/client/sessions",
            json={"game_id": str(game.id), "device_id": device_id},
        )

        device_service = DeviceService(db_session)
        device = await device_service.repository.get_by_game_and_device_id(game.id, device_id)
        assert device is not None

        # Manually create an expired nonce
        expired_nonce = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired 1 second ago
            status="pending",
        )
        db_session.add(expired_nonce)
        await db_session.commit()

        # Try to use expired nonce
        nonce_service = NonceService(db_session)
        with pytest.raises(ValueError, match="expired"):
            await nonce_service.validate_and_consume_nonce(expired_nonce.nonce_value, device.id)
