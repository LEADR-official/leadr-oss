"""Tests for Identity API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.common.domain.ids import AccountID
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestIdentityRoutes:
    """Test suite for Identity API routes."""

    async def test_list_identities(self, client: AsyncClient, db_session, test_api_key):
        """Test listing identities via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identities
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345678-1234-1234-1234-123456789012",
            display_name="Player One",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.STEAM,
            external_key="76561198012345678",
            display_name="Player Two",
        )

        # List identities
        response = await client.get(
            f"/identities?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        external_keys = {i["external_key"] for i in data["data"]}
        assert "dev_12345678-1234-1234-1234-123456789012" in external_keys
        assert "76561198012345678" in external_keys

    async def test_list_identities_filter_by_game(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering identities by game_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-game",
        )

        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create identities for both games
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_game1_identity",
        )
        await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_game2_identity",
        )

        # Filter by game1
        response = await client.get(
            f"/identities?account_id={account.id}&game_id={game1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["external_key"] == "dev_game1_identity"

    async def test_list_identities_filter_by_kind(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering identities by kind via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-kind",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identities with different kinds
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_device_identity",
        )
        await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.STEAM,
            external_key="76561198012345678",
        )

        # Filter by DEVICE kind
        response = await client.get(
            f"/identities?account_id={account.id}&kind=DEVICE",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["external_key"] == "dev_device_identity"
        assert data["data"][0]["kind"] == "DEVICE"

    async def test_list_identities_invalid_kind(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering identities with invalid kind returns 400."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-invalid-kind",
        )

        # Filter by invalid kind
        response = await client.get(
            f"/identities?account_id={account.id}&kind=INVALID_KIND",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "Invalid kind" in response.json()["error"]

    async def test_get_identity(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single identity by ID via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-get",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_get_test_identity",
            display_name="Test Player",
        )

        # Get identity
        response = await client.get(
            f"/identities/{identity.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(identity.id)
        assert data["external_key"] == "dev_get_test_identity"
        assert data["display_name"] == "Test Player"
        assert data["kind"] == "DEVICE"

    async def test_get_identity_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent identity returns 404."""
        response = await client.get(
            "/identities/ide_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_update_identity_display_name(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test updating identity display name via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-update",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_test_identity",
            display_name="Original Name",
        )

        # Update display name
        response = await client.patch(
            f"/identities/{identity.id}",
            json={"display_name": "New Display Name"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "New Display Name"

    async def test_soft_delete_identity(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting an identity via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp-identity-delete",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_delete_test_identity",
        )

        # Soft delete
        response = await client.patch(
            f"/identities/{identity.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify it's deleted (shouldn't appear in list)
        list_response = await client.get(
            f"/identities?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )
        assert list_response.status_code == 200
        data = list_response.json()
        external_keys = [i["external_key"] for i in data["data"]]
        assert "dev_delete_test_identity" not in external_keys

    async def test_superadmin_list_identities_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list identities WITHOUT account_id and sees all accounts."""
        # Create two accounts with identities in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Identities",
            slug="account-one-identities",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Identities",
            slug="account-two-identities",
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
            name="Game Account 1 Identity",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Account 2 Identity",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        await identity_service.get_or_create_identity(
            account_id=account1.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_test_1",
        )
        await identity_service.get_or_create_identity(
            account_id=account2.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_test_2",
        )

        # List identities WITHOUT account_id - should return identities from ALL accounts
        response = await authenticated_client.get("/identities")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain identities from both accounts
        external_keys = {i["external_key"] for i in data["data"]}
        assert "dev_superadmin_test_1" in external_keys
        assert "dev_superadmin_test_2" in external_keys
