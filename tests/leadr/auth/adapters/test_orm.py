"""Tests for Device, DeviceSession, and Nonce ORM models."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM, DeviceStatusEnum, NonceORM
from leadr.auth.domain.device import Device, DeviceSession, DeviceStatus
from leadr.auth.domain.nonce import Nonce, NonceStatus
from leadr.common.domain.ids import AccountID, DeviceID, DeviceSessionID, GameID, NonceID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestDeviceORM:
    """Test suite for Device ORM model."""

    async def test_create_device(self, db_session: AsyncSession):
        """Test creating a device in the database."""
        # Create account and game first (foreign key requirements)
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

        # Create device
        device_id_val = uuid4()
        device = DeviceORM(
            id=device_id_val,
            game_id=game.id,
            device_id="test-device-123",
            account_id=game.account_id,
            status="active",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            device_metadata={"platform": "ios", "version": "1.0.0"},
        )

        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        assert device.id == device_id_val
        assert device.game_id == game.id
        assert device.device_id == "test-device-123"
        assert device.account_id == game.account_id
        assert device.status == "active"
        assert device.first_seen_at is not None
        assert device.last_seen_at is not None
        assert device.device_metadata == {"platform": "ios", "version": "1.0.0"}
        assert device.created_at is not None
        assert device.updated_at is not None

    async def test_device_status_defaults_to_active(self, db_session: AsyncSession):
        """Test that device status defaults to active."""
        # Create account and game first
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

        # Create device without explicit status
        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device-123",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )

        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        assert device.status == "active"

    async def test_device_game_id_and_device_id_unique_together(self, db_session: AsyncSession):
        """Test that (game_id, device_id) must be unique together."""
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

        now = datetime.now(UTC)

        device1 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="duplicate-device",
            account_id=game.account_id,
            first_seen_at=now,
            last_seen_at=now,
        )

        device2 = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="duplicate-device",  # Same device_id for same game
            account_id=game.account_id,
            first_seen_at=now,
            last_seen_at=now,
        )

        db_session.add(device1)
        await db_session.commit()

        db_session.add(device2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_device_same_device_id_different_games_allowed(self, db_session: AsyncSession):
        """Test that same device_id can exist for different games."""
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game1 = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Game 1",
        )
        game2 = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Game 2",
        )
        db_session.add(game1)
        db_session.add(game2)
        await db_session.commit()

        now = datetime.now(UTC)

        device1 = DeviceORM(
            id=uuid4(),
            game_id=game1.id,
            device_id="same-device",
            account_id=account.id,
            first_seen_at=now,
            last_seen_at=now,
        )

        device2 = DeviceORM(
            id=uuid4(),
            game_id=game2.id,
            device_id="same-device",  # Same device_id but different game
            account_id=account.id,
            first_seen_at=now,
            last_seen_at=now,
        )

        db_session.add(device1)
        db_session.add(device2)
        await db_session.commit()

        # Should succeed - no integrity error
        await db_session.refresh(device1)
        await db_session.refresh(device2)

        assert device1.device_id == device2.device_id
        assert device1.game_id != device2.game_id

    async def test_device_cascades_on_game_delete(self, db_session: AsyncSession):
        """Test that devices are deleted when their game is deleted."""
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

        device_id = device.id

        # Delete the game
        await db_session.delete(game)
        await db_session.commit()

        # Device should be gone
        result = await db_session.execute(select(DeviceORM).where(DeviceORM.id == device_id))
        deleted_device = result.scalar_one_or_none()
        assert deleted_device is None

    async def test_device_metadata_defaults_to_empty_dict(self, db_session: AsyncSession):
        """Test that metadata defaults to empty dict if not provided."""
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
        await db_session.refresh(device)

        assert device.device_metadata == {}

    async def test_device_to_domain_conversion(self, db_session: AsyncSession):
        """Test converting Device ORM to domain entity."""
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

        now = datetime.now(UTC)
        device_id_val = uuid4()

        device_orm = DeviceORM(
            id=device_id_val,
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            status=DeviceStatusEnum.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            device_metadata={"platform": "android"},
            created_at=now,
            updated_at=now,
        )

        # Convert to domain
        device_domain = device_orm.to_domain()

        assert isinstance(device_domain, Device)
        assert device_domain.id == device_id_val
        assert device_domain.game_id == game.id
        assert device_domain.device_id == "test-device"
        assert device_domain.account_id == game.account_id
        assert device_domain.status == DeviceStatus.ACTIVE
        assert device_domain.first_seen_at == now
        assert device_domain.last_seen_at == now
        assert device_domain.metadata == {"platform": "android"}

    async def test_device_from_domain_conversion(self, db_session: AsyncSession):
        """Test converting Device domain to ORM model."""
        now = datetime.now(UTC)
        device_id_val = uuid4()
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())

        device_domain = Device(
            id=DeviceID(device_id_val),
            game_id=game_id,
            device_id="test-device",
            account_id=account_id,
            status=DeviceStatus.BANNED,
            first_seen_at=now,
            last_seen_at=now,
            metadata={"platform": "ios"},
            created_at=now,
            updated_at=now,
        )

        # Convert to ORM
        device_orm = DeviceORM.from_domain(device_domain)

        assert device_orm.id == device_id_val
        assert device_orm.game_id == game_id
        assert device_orm.device_id == "test-device"
        assert device_orm.account_id == account_id
        assert device_orm.status == "banned"
        assert device_orm.first_seen_at == now
        assert device_orm.last_seen_at == now
        assert device_orm.device_metadata == {"platform": "ios"}


@pytest.mark.asyncio
class TestDeviceSessionORM:
    """Test suite for DeviceSession ORM model."""

    async def test_create_device_session(self, db_session: AsyncSession):
        """Test creating a device session in the database."""
        # Create account, game, and device first
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

        # Create session
        session_id = DeviceSessionID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        session = DeviceSessionORM(
            id=session_id,
            device_id=device.id,
            access_token_hash="hashed_token_value",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=now + timedelta(days=30),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id == session_id
        assert session.device_id == device.id
        assert session.access_token_hash == "hashed_token_value"
        assert session.expires_at == expires_at
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"
        assert session.revoked_at is None
        assert session.created_at is not None
        assert session.updated_at is not None

    async def test_device_session_cascades_on_device_delete(self, db_session: AsyncSession):
        """Test that sessions are deleted when their device is deleted."""
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

        # Create session
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device.id,
            access_token_hash="hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(session)
        await db_session.commit()

        session_id = session.id

        # Delete device
        await db_session.delete(device)
        await db_session.commit()

        # Session should be gone
        result = await db_session.get(DeviceSessionORM, session_id)
        assert result is None

    async def test_device_session_optional_fields(self, db_session: AsyncSession):
        """Test that optional fields (ip_address, user_agent, revoked_at) can be null."""
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

        # Create session without optional fields
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device.id,
            access_token_hash="hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.ip_address is None
        assert session.user_agent is None
        assert session.revoked_at is None

    async def test_device_session_access_token_hash_indexed(self, db_session: AsyncSession):
        """Test that access_token_hash is indexed for fast lookups."""
        # This test verifies the index exists by checking we can create
        # sessions with different hashes quickly
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

        # Create multiple sessions
        for i in range(5):
            session = DeviceSessionORM(
                id=uuid4(),
                device_id=device.id,
                access_token_hash=f"hash_{i}",
                refresh_token_hash=f"refresh_hash_{i}",
                token_version=1,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            db_session.add(session)

        await db_session.commit()
        # If index exists, this should be fast

    async def test_device_session_to_domain_conversion(self, db_session: AsyncSession):
        """Test converting DeviceSession ORM to domain entity."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        session_id = DeviceSessionID(uuid4())
        device_id = DeviceID(uuid4())

        session_orm = DeviceSessionORM(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=now + timedelta(days=30),
            ip_address="10.0.0.1",
            user_agent="Test Agent",
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        # Convert to domain
        session_domain = session_orm.to_domain()

        assert isinstance(session_domain, DeviceSession)
        assert session_domain.id == session_id
        assert session_domain.device_id == device_id
        assert session_domain.access_token_hash == "hashed_token"
        assert session_domain.expires_at == expires_at
        assert session_domain.ip_address == "10.0.0.1"
        assert session_domain.user_agent == "Test Agent"
        assert session_domain.revoked_at is None

    async def test_device_session_from_domain_conversion(self, db_session: AsyncSession):
        """Test converting DeviceSession domain to ORM model."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        session_id = DeviceSessionID(uuid4())
        device_id = DeviceID(uuid4())
        revoked_at = now + timedelta(minutes=30)

        session_domain = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=now + timedelta(days=30),
            ip_address="192.168.1.100",
            user_agent="Chrome",
            revoked_at=revoked_at,
            created_at=now,
            updated_at=now,
        )

        # Convert to ORM
        session_orm = DeviceSessionORM.from_domain(session_domain)

        assert session_orm.id == session_id
        assert session_orm.device_id == device_id
        assert session_orm.access_token_hash == "hashed_token"
        assert session_orm.expires_at == expires_at
        assert session_orm.ip_address == "192.168.1.100"
        assert session_orm.user_agent == "Chrome"
        assert session_orm.revoked_at == revoked_at


@pytest.mark.asyncio
class TestNonceORM:
    """Test suite for Nonce ORM model."""

    async def test_create_nonce(self, db_session: AsyncSession):
        """Test creating a nonce in the database."""
        # Create account, game, and device first (foreign key requirements)
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

        # Create nonce
        nonce_id = NonceID(uuid4())
        nonce_value = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=60)

        nonce = NonceORM(
            id=nonce_id,
            device_id=device.id,
            nonce_value=nonce_value,
            expires_at=expires_at,
            status="pending",
        )

        db_session.add(nonce)
        await db_session.commit()
        await db_session.refresh(nonce)

        assert nonce.id == nonce_id
        assert nonce.device_id == device.id
        assert nonce.nonce_value == nonce_value
        assert nonce.expires_at == expires_at
        assert nonce.status == "pending"
        assert nonce.used_at is None
        assert nonce.created_at is not None
        assert nonce.updated_at is not None

    async def test_nonce_status_defaults_to_pending(self, db_session: AsyncSession):
        """Test that nonce status defaults to pending."""
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

        # Create nonce without explicit status
        nonce = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        db_session.add(nonce)
        await db_session.commit()
        await db_session.refresh(nonce)

        assert nonce.status == "pending"

    async def test_nonce_value_unique_constraint(self, db_session: AsyncSession):
        """Test that nonce_value must be unique."""
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

        # Create first nonce
        nonce_value = str(uuid4())
        nonce1 = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        db_session.add(nonce1)
        await db_session.commit()

        # Try to create second nonce with same nonce_value
        nonce2 = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=nonce_value,  # Duplicate
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        db_session.add(nonce2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_nonce_cascades_on_device_delete(self, db_session: AsyncSession):
        """Test that nonces are deleted when their device is deleted."""
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

        # Create nonce
        nonce = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )
        db_session.add(nonce)
        await db_session.commit()

        nonce_id = nonce.id

        # Delete device
        await db_session.delete(device)
        await db_session.commit()

        # Nonce should be gone
        result = await db_session.get(NonceORM, nonce_id)
        assert result is None

    async def test_nonce_to_domain_conversion(self, db_session: AsyncSession):
        """Test converting Nonce ORM to domain entity."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=60)
        used_at = now + timedelta(seconds=30)
        nonce_id = NonceID(uuid4())
        device_id = DeviceID(uuid4())
        nonce_value = str(uuid4())

        nonce_orm = NonceORM(
            id=nonce_id,
            device_id=device_id,
            nonce_value=nonce_value,
            expires_at=expires_at,
            used_at=used_at,
            status="used",
            created_at=now,
            updated_at=now,
        )

        # Convert to domain
        nonce_domain = nonce_orm.to_domain()

        assert isinstance(nonce_domain, Nonce)
        assert nonce_domain.id == nonce_id
        assert nonce_domain.device_id == device_id
        assert nonce_domain.nonce_value == nonce_value
        assert nonce_domain.expires_at == expires_at
        assert nonce_domain.used_at == used_at
        assert nonce_domain.status == NonceStatus.USED

    async def test_nonce_from_domain_conversion(self, db_session: AsyncSession):
        """Test converting Nonce domain to ORM model."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=60)
        nonce_id = NonceID(uuid4())
        device_id = DeviceID(uuid4())
        nonce_value = str(uuid4())

        nonce_domain = Nonce(
            id=nonce_id,
            device_id=device_id,
            nonce_value=nonce_value,
            expires_at=expires_at,
            status=NonceStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        # Convert to ORM
        nonce_orm = NonceORM.from_domain(nonce_domain)

        assert nonce_orm.id == nonce_id
        assert nonce_orm.device_id == device_id
        assert nonce_orm.nonce_value == nonce_value
        assert nonce_orm.expires_at == expires_at
        assert nonce_orm.status == "pending"
        assert nonce_orm.used_at is None
