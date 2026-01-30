"""Test configuration and fixtures."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from aiosmtpd.controller import Controller
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.main import create_app

# Import all ORM models to register them with SQLAlchemy metadata
from leadr.accounts.adapters.orm import AccountORM, UserORM  # noqa: F401
from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.dependencies import get_user_service
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.auth.adapters.orm import APIKeyORM  # noqa: F401
from leadr.auth.dependencies import (
    AdminAuthContext,
    ClientAuthContext,
)
from leadr.auth.domain.api_key import APIKey
from leadr.auth.domain.device import Device
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.dependencies import get_api_key_service
from leadr.auth.services.repositories import DeviceRepository
from leadr.boards.adapters.orm import BoardORM  # noqa: F401
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.services.repositories import BoardRepository
from leadr.common.database import get_db
from leadr.common.domain.ids import (
    AccountID,
    APIKeyID,
    BoardID,
    DeviceID,
    GameID,
    IdentityID,
    UserID,
)
from leadr.common.orm import Base
from leadr.config import settings
from leadr.games.adapters.orm import GameORM  # noqa: F401
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.infra.email.adapters.orm import EmailORM  # noqa: F401
from leadr.registration.adapters.orm import (  # noqa: F401
    JamCodeORM,
    JamCodeRedemptionORM,
    VerificationCodeORM,
)
from leadr.scores.adapters.orm import ScoreFlagORM, ScoreSubmissionMetaORM  # noqa: F401

# Import all ORM fixtures from fixtures module
from tests.fixtures import *  # noqa: F403, F401


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session for unit tests that don't need real DB."""
    return MagicMock(spec=AsyncSession)


# ---------------------------------------------------------------------------
# Shared fixtures for isolated API unit tests (no database)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mock_client_no_db(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client that blocks all database access.

    Any service or dependency that attempts to use the database session
    will raise RuntimeError, ensuring tests are fully isolated.
    """

    async def noop_get_db() -> AsyncGenerator[AsyncSession, None]:
        raise RuntimeError("Unit tests must not use the database")
        yield  # noqa: RET503 — unreachable, keeps it an async generator

    test_app.dependency_overrides[get_db] = noop_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url=f"http://testserver{settings.API_PREFIX}",
    ) as c:
        yield c

    test_app.dependency_overrides.clear()


def make_admin_auth(
    account_id: AccountID | None = None,
    is_superadmin: bool = True,
) -> AdminAuthContext:
    """Factory for creating mock AdminAuthContext instances.

    Args:
        account_id: Account ID. Auto-generated if not provided.
        is_superadmin: Whether the user is a superadmin.
    """
    account_id = account_id or AccountID()
    user_id = UserID()

    user = User(
        id=user_id,
        account_id=account_id,
        email="test@example.com",
        display_name="Test User",
        super_admin=is_superadmin,
    )

    api_key = APIKey(
        id=APIKeyID(),
        account_id=account_id,
        user_id=user_id,
        name="Test Key",
        key_hash="fakehash",
        key_prefix="ldr_test",
    )

    return AdminAuthContext(
        account_id=account_id,
        user=user,
        api_key=api_key,
    )


def make_client_auth(
    account_id: AccountID | None = None,
    game_id: GameID | None = None,
    identity_id: IdentityID | None = None,
    test_mode: bool = False,
) -> ClientAuthContext:
    """Factory for creating mock ClientAuthContext instances.

    Args:
        account_id: Account ID. Auto-generated if not provided.
        game_id: Game ID. Auto-generated if not provided.
        identity_id: Identity ID. Auto-generated if not provided.
        test_mode: Whether the session is in test mode.
    """
    account_id = account_id or AccountID()
    game_id = game_id or GameID()
    identity_id = identity_id or IdentityID()

    identity = Identity(
        id=identity_id,
        account_id=account_id,
        game_id=game_id,
        kind=IdentityKind.DEVICE,
        external_key="test-device-key",
        display_name="Player1",
    )

    return ClientAuthContext(
        account_id=account_id,
        identity=identity,
        test_mode=test_mode,
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment():
    """
    SAFETY CHECK: Ensure we're running in TEST environment.

    This prevents accidentally running tests against dev/prod databases
    and losing data when tests drop/recreate databases.
    """
    if settings.ENV != "TEST":
        print("\n🚨 DANGER: Tests must run in TEST environment!")
        print(f"Current ENV: {settings.ENV}")
        print("Expected: TEST")
        print("\nTo fix: Set ENV=TEST in your environment or use .env.test file")
        print("This safety check prevents accidentally deleting your dev database!\n")
        sys.exit(1)


def pytest_sessionfinish(session, exitstatus):
    """
    Clean up test database even on keyboard interrupt.

    This hook is called after all tests finish, including when tests are
    interrupted with Ctrl+C. It ensures the test database is dropped
    regardless of how pytest exits.
    """
    test_database_name = session.config.cache.get("test_database_name", None)

    if test_database_name:
        admin_url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"

        try:
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                # Terminate active connections
                conn.execute(
                    text(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{test_database_name}' AND pid <> pg_backend_pid()
                """)
                )
                conn.execute(text(f'DROP DATABASE IF EXISTS "{test_database_name}"'))
            admin_engine.dispose()
        except Exception as e:
            # Don't let cleanup errors break the test run
            print(f"\nWarning: Failed to cleanup test database {test_database_name}: {e}")


@pytest.fixture(scope="session")
def test_database_name():
    """Generate unique test database name for the session."""
    return f"leadr_test_{str(uuid4())[:8]}"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_database_name: str, request):
    """Create and destroy test database for the session (sync fixture)."""
    # Use sync psycopg for database creation/destruction to avoid event loop issues

    # Store database name in pytest config for cleanup hook
    request.config.cache.set("test_database_name", test_database_name)

    admin_url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    # Create test database
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_database_name}"'))
        conn.execute(text(f'CREATE DATABASE "{test_database_name}"'))

    admin_engine.dispose()

    yield

    # Clean up: drop test database
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Terminate active connections
        conn.execute(
            text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_database_name}' AND pid <> pg_backend_pid()
        """)
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_database_name}"'))
    admin_engine.dispose()

    # Clear from cache after successful cleanup
    request.config.cache.set("test_database_name", None)


@pytest_asyncio.fixture(scope="function")
async def test_engine(test_database_name: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for the test database (function-scoped to avoid event loop issues)."""
    test_database_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_database_name}"

    engine = create_async_engine(
        test_database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DB_ECHO,
    )

    # Create all tables (idempotent - won't fail if tables exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Truncate all tables after test for isolation (faster than drop/create)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as cleanup_session:
        for table in reversed(Base.metadata.sorted_tables):
            await cleanup_session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await cleanup_session.commit()

    # Dispose engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for each test.

    Table truncation is handled by the test_engine fixture cleanup.
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@asynccontextmanager
async def noop_lifespan(app):
    """No-op lifespan for tests - skips GeoIP, scheduler, superadmin bootstrap."""
    yield


@pytest.fixture
def test_app():
    """Create test app instance for dependency overrides.

    Tests that need to set dependency_overrides should request this fixture
    in addition to client/authenticated_client.
    """
    return create_app(lifespan_override=noop_lifespan)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""

    # Override the get_db dependency to use our test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url=f"http://testserver{settings.API_PREFIX}",
    ) as client:
        yield client

    # Clean up overrides
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def smtp_server():
    """
    Start an SMTP debugging server for testing email sending.

    The server runs on localhost:1025 and captures all emails sent to it.
    Emails are stored in memory and can be accessed via the `messages` attribute.

    Yields:
        A tuple of (server_controller, messages_list) where:
        - server_controller: The aiosmtpd Controller instance
        - messages_list: A list that collects all sent emails as (envelope, content) tuples
    """
    messages = []

    class TestHandler:
        """Handler that captures emails in memory."""

        async def handle_DATA(self, server, session, envelope):  # noqa: N802
            """Handle email data - store in messages list."""
            messages.append(
                {
                    "envelope": envelope,
                    "from": envelope.mail_from,
                    "to": envelope.rcpt_tos,
                    "data": envelope.content.decode("utf-8", errors="replace"),
                }
            )
            return "250 Message accepted for delivery"

    controller = Controller(TestHandler(), hostname="localhost", port=1025)
    controller.start()

    # Give server time to start
    await asyncio.sleep(0.1)

    yield controller, messages

    controller.stop()


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession) -> Account:
    """Create a test account for use in tests.

    Returns:
        The created Account domain entity.
    """
    account_repo = AccountRepository(db_session)
    account_id = AccountID()
    now = datetime.now(UTC)

    account = Account(
        id=account_id,
        name="Test Account",
        slug=f"test-{str(account_id.uuid)[:8]}",  # Unique slug using UUID prefix
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    return await account_repo.create(account)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_account: Account):
    """Create a test user for use in tests.

    Returns:
        The created User domain entity.
    """

    user_repo = UserRepository(db_session)
    user_id = UserID()
    now = datetime.now(UTC)

    user = User(
        id=user_id,
        account_id=test_account.id,
        email=f"test-user-{str(user_id.uuid)[:8]}@example.com",
        display_name="Test User",
        created_at=now,
        updated_at=now,
    )
    return await user_repo.create(user)


@pytest_asyncio.fixture
async def test_game(db_session: AsyncSession, test_account: Account):
    """Create a test game for use in tests.

    Returns:
        The created Game domain entity.
    """

    game_repo = GameRepository(db_session)
    game_id = GameID()
    now = datetime.now(UTC)

    game = Game(
        id=game_id,
        account_id=test_account.id,
        name="Test Game",
        slug="test-game",
        created_at=now,
        updated_at=now,
    )
    return await game_repo.create(game)


@pytest_asyncio.fixture
async def test_device(db_session: AsyncSession, test_account: Account, test_game):
    """Create a test device for use in tests.

    Returns:
        The created Device domain entity.
    """

    device_repo = DeviceRepository(db_session)
    device_id = DeviceID()
    now = datetime.now(UTC)

    device = Device(
        id=device_id,
        account_id=test_account.id,
        game_id=test_game.id,
        client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    return await device_repo.create(device)


@pytest_asyncio.fixture
async def test_board(db_session: AsyncSession, test_account: Account, test_game):
    """Create a test board for use in tests.

    Returns:
        The created Board domain entity.
    """

    board_repo = BoardRepository(db_session)
    board_id = BoardID()
    now = datetime.now(UTC)

    board = Board(
        id=board_id,
        account_id=test_account.id,
        game_id=test_game.id,
        name="Test Board",
        slug="test-board",
        icon="trophy",
        short_code=f"TEST{str(board_id.uuid)[:6]}".upper(),
        unit="points",
        is_active=True,
        sort_direction=SortDirection.DESCENDING,
        keep_strategy=KeepStrategy.BEST,  # Use ALL to keep all scores for testing
        created_at=now,
        updated_at=now,
    )
    return await board_repo.create(board)


@pytest_asyncio.fixture
async def run_runs_board(db_session: AsyncSession, test_account: Account, test_game):
    """Create a RUN_RUNS board that keeps all score submissions.

    Use this fixture for tests that need to create multiple scores from the same
    device/identity and have all of them stored (pagination tests, around tests).

    Returns:
        The created Board domain entity.
    """
    board_repo = BoardRepository(db_session)
    board_id = BoardID()
    now = datetime.now(UTC)

    board = Board(
        id=board_id,
        account_id=test_account.id,
        game_id=test_game.id,
        name="Test Board (RUN_RUNS)",
        slug="test-board-run-runs",
        icon="trophy",
        short_code=f"RUNS{str(board_id.uuid)[:6]}".upper(),
        unit="points",
        is_active=True,
        sort_direction=SortDirection.DESCENDING,
        board_type=BoardType.RUN_RUNS,
        keep_strategy=KeepStrategy.NA,
        created_at=now,
        updated_at=now,
    )
    return await board_repo.create(board)


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession) -> str:
    """Create a test account, user, and API key, return the plain key.

    This fixture provides a valid API key that can be used to authenticate
    requests to protected endpoints during testing.

    Returns:
        The plain API key string that can be used in the leadr-api-key header.
    """
    # Create test account with unique slug to avoid conflicts
    account_repo = AccountRepository(db_session)
    account_id = AccountID()
    now = datetime.now(UTC)

    account = Account(
        id=account_id,
        name="Test Account for Auth",
        slug=f"test-auth-{str(account_id.uuid)[:8]}",  # Unique slug using UUID prefix
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await account_repo.create(account)

    # Create test user for the API key (superadmin to allow access to all accounts)
    user_service = await get_user_service(db_session)
    user = await user_service.create_user(
        account_id=account_id,
        email=f"test-{str(account_id.uuid)[:8]}@example.com",
        display_name="Test User",
        super_admin=True,
    )

    # Create API key using dependency factory
    service = await get_api_key_service(db_session)
    _, plain_key = await service.create_api_key(
        account_id=account_id,
        user_id=user.id,
        name="Test API Key",
        expires_at=None,
    )

    return plain_key


@pytest_asyncio.fixture
async def authenticated_client(
    db_session: AsyncSession, test_api_key: str, test_app
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with API key authentication.

    This client automatically includes the API key in all requests,
    allowing tests to easily access protected endpoints.
    """

    # Override the get_db dependency to use our test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url=f"http://testserver{settings.API_PREFIX}",
        headers={"leadr-api-key": test_api_key},
    ) as client:
        yield client

    # Clean up overrides
    test_app.dependency_overrides.clear()
