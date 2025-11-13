"""Tests for NonceService."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, NonceORM
from leadr.auth.domain.nonce import NonceStatus
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import DeviceID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestNonceService:
    """Test suite for NonceService."""

    async def test_generate_nonce_creates_nonce_with_default_ttl(self, db_session: AsyncSession):
        """Test generating a nonce with default TTL."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, expires_at = await service.generate_nonce(device_id=DeviceID(device.id))

        # Verify nonce was created
        assert nonce_value is not None
        assert len(nonce_value) == 36  # UUID string length

        # Verify expiry is approximately 60 seconds from now (default TTL)
        expected_expiry = datetime.now(UTC) + timedelta(seconds=60)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

    async def test_generate_nonce_creates_nonce_with_custom_ttl(self, db_session: AsyncSession):
        """Test generating a nonce with custom TTL."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Generate nonce with 120 second TTL
        service = NonceService(db_session)
        nonce_value, expires_at = await service.generate_nonce(
            device_id=DeviceID(device.id), ttl_seconds=120
        )

        # Verify expiry is approximately 120 seconds from now
        expected_expiry = datetime.now(UTC) + timedelta(seconds=120)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    async def test_generate_nonce_stores_in_database(self, db_session: AsyncSession):
        """Test that generated nonce is stored in database."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(device_id=DeviceID(device.id))

        # Verify nonce exists in database
        repository = service.repository
        nonce = await repository.get_by_nonce_value(nonce_value)

        assert nonce is not None
        assert nonce.nonce_value == nonce_value
        assert nonce.device_id == DeviceID(device.id)
        assert nonce.status == NonceStatus.PENDING

    async def test_validate_and_consume_nonce_success(self, db_session: AsyncSession):
        """Test successfully validating and consuming a nonce."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(device_id=DeviceID(device.id))

        # Validate and consume
        result = await service.validate_and_consume_nonce(nonce_value, DeviceID(device.id))

        assert result is True

        # Verify nonce is marked as used
        repository = service.repository
        nonce = await repository.get_by_nonce_value(nonce_value)

        assert nonce is not None
        assert nonce.status == NonceStatus.USED
        assert nonce.used_at is not None

    async def test_validate_and_consume_nonce_not_found(self, db_session: AsyncSession):
        """Test that validating unknown nonce raises ValueError."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Try to validate unknown nonce
        service = NonceService(db_session)

        with pytest.raises(ValueError, match="Nonce not found"):
            await service.validate_and_consume_nonce("unknown-nonce", DeviceID(device.id))

    async def test_validate_and_consume_nonce_wrong_device(self, db_session: AsyncSession):
        """Test that using nonce from different device raises ValueError."""
        # Create account, game, and two devices
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device1 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-1",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device1)

        device2 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-2",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device2)
        await db_session.commit()

        # Generate nonce for device1
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(device_id=DeviceID(device1.id))

        # Try to use nonce with device2
        with pytest.raises(ValueError, match="Nonce does not belong to this device"):
            await service.validate_and_consume_nonce(nonce_value, DeviceID(device2.id))

    async def test_validate_and_consume_nonce_already_used(self, db_session: AsyncSession):
        """Test that using nonce twice raises ValueError."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Generate and use nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(device_id=DeviceID(device.id))
        await service.validate_and_consume_nonce(nonce_value, DeviceID(device.id))

        # Try to use same nonce again
        with pytest.raises(ValueError, match="Nonce already used"):
            await service.validate_and_consume_nonce(nonce_value, DeviceID(device.id))

    async def test_validate_and_consume_nonce_expired(self, db_session: AsyncSession):
        """Test that using expired nonce raises ValueError."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Create expired nonce directly in DB
        expired_nonce = NonceORM(
            id=uuid4(),
            device_id=DeviceID(device.id),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired
            status="pending",
        )
        db_session.add(expired_nonce)
        await db_session.commit()

        # Try to use expired nonce
        service = NonceService(db_session)

        with pytest.raises(ValueError, match="Nonce expired"):
            await service.validate_and_consume_nonce(expired_nonce.nonce_value, DeviceID(device.id))

    async def test_cleanup_expired_nonces_deletes_old_nonces(self, db_session: AsyncSession):
        """Test that cleanup deletes old expired nonces."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Create old expired nonce (expired 25 hours ago)
        old_nonce = NonceORM(
            id=uuid4(),
            device_id=DeviceID(device.id),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=25),
            status="pending",
        )
        db_session.add(old_nonce)

        # Create recent expired nonce (expired 30 minutes ago)
        recent_nonce = NonceORM(
            id=uuid4(),
            device_id=DeviceID(device.id),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(minutes=30),
            status="pending",
        )
        db_session.add(recent_nonce)

        await db_session.commit()

        # Cleanup nonces older than 24 hours
        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        # Should delete only the old nonce
        assert deleted_count == 1

        # Verify old nonce is gone
        repository = service.repository
        old_retrieved = await repository.get_by_id(old_nonce.id)
        assert old_retrieved is None

        # Verify recent nonce still exists
        recent_retrieved = await repository.get_by_id(recent_nonce.id)
        assert recent_retrieved is not None

    async def test_cleanup_expired_nonces_returns_zero_when_none_to_delete(
        self, db_session: AsyncSession
    ):
        """Test that cleanup returns 0 when there are no nonces to delete."""
        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        assert deleted_count == 0

    async def test_multiple_devices_can_have_pending_nonces(self, db_session: AsyncSession):
        """Test that multiple devices can have pending nonces simultaneously."""
        # Create account, game, and two devices
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device1 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-1",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device1)

        device2 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-2",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device2)
        await db_session.commit()

        # Generate nonces for both devices
        service = NonceService(db_session)
        nonce1, _ = await service.generate_nonce(device_id=DeviceID(device1.id))
        nonce2, _ = await service.generate_nonce(device_id=DeviceID(device2.id))

        # Both nonces should be unique and valid
        assert nonce1 != nonce2

        # Each device can use its own nonce
        result1 = await service.validate_and_consume_nonce(nonce1, DeviceID(device1.id))
        result2 = await service.validate_and_consume_nonce(nonce2, DeviceID(device2.id))

        assert result1 is True
        assert result2 is True
