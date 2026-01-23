"""Tests for Identity Session API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.identity_service import IdentityService
from leadr.common.api.pagination import PaginationParams
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestIdentitySessionRoutes:
    """Test suite for Identity Session API routes."""

    async def test_list_sessions(self, client: AsyncClient, db_session, test_api_key):
        """Test listing identity sessions via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-sessions",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identities and sessions
        identity_service = IdentityService(db_session)
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_list_test_1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_list_test_2",
        )

        # Start sessions
        await identity_service.start_session(identity1)
        await identity_service.start_session(identity2)

        # List sessions
        response = await client.get(
            f"/identity-sessions?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2

    async def test_list_sessions_filter_by_identity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering sessions by identity_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-session-filter",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identities and sessions
        identity_service = IdentityService(db_session)
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_filter_test_1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_filter_test_2",
        )

        # Start sessions
        await identity_service.start_session(identity1)
        await identity_service.start_session(identity2)

        # Filter by identity1
        response = await client.get(
            f"/identity-sessions?account_id={account.id}&identity_id={identity1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["identity_id"] == str(identity1.id)

    async def test_get_session(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single identity session by ID via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-session-get",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identity and session
        identity_service = IdentityService(db_session)
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_get_test",
        )
        await identity_service.start_session(identity)

        # Get the session
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await identity_service.list_sessions(
            account_id=account.id,
            identity_id=identity.id,
            pagination=pagination,
        )
        session = result.items[0]

        # Get session via API
        response = await client.get(
            f"/identity-sessions/{session.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session.id)
        assert data["identity_id"] == str(identity.id)

    async def test_get_session_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent session returns 404."""
        response = await client.get(
            "/identity-sessions/ses_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_revoke_session(self, client: AsyncClient, db_session, test_api_key):
        """Test revoking an identity session via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-session-revoke",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identity and session
        identity_service = IdentityService(db_session)
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_session_revoke_test",
        )
        await identity_service.start_session(identity)

        # Get the session
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await identity_service.list_sessions(
            account_id=account.id,
            identity_id=identity.id,
            pagination=pagination,
        )
        session = result.items[0]

        # Revoke session
        response = await client.delete(
            f"/identity-sessions/{session.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_at"] is not None

    async def test_superadmin_list_sessions_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list sessions WITHOUT account_id and sees all accounts."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.common.domain.ids import AccountID

        # Create two accounts with identities/sessions in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Identity Sessions",
            slug="account-one-identity-sessions",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Identity Sessions",
            slug="account-two-identity-sessions",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games and identities for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Account 1 Session",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Account 2 Session",
        )

        identity_service = IdentityService(db_session)
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account1.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_session_test_1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account2.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_session_test_2",
        )

        # Start sessions
        await identity_service.start_session(identity1)
        await identity_service.start_session(identity2)

        # List sessions WITHOUT account_id - should return sessions from ALL accounts
        response = await authenticated_client.get("/identity-sessions")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain sessions from both accounts (at least 2)
        assert len(data["data"]) >= 2
