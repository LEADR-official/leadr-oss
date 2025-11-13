"""Integration tests for authorization and multi-tenant access control."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.dependencies import get_user_service
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.domain.ids import AccountID, GameID
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


@pytest.mark.asyncio
class TestSuperadminAuthorization:
    """Test suite for superadmin cross-account access."""

    async def test_superadmin_can_create_accounts(self, authenticated_client: AsyncClient):
        """Test that superadmin can create accounts (regular users cannot)."""
        response = await authenticated_client.post(
            "/accounts",
            json={
                "name": "New Account",
                "slug": "new-account",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Account"
        assert data["slug"] == "new-account"

    async def test_superadmin_can_list_all_accounts(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can see all accounts."""
        # Create two additional accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One",
            slug="account-one",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two",
            slug="account-two",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # List all accounts
        response = await authenticated_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        # Should see at least the two we just created plus the auth fixture account
        assert len(data) >= 3
        account_names = {acc["name"] for acc in data}
        assert "Account One" in account_names
        assert "Account Two" in account_names

    async def test_superadmin_can_access_any_account(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can access resources from any account."""
        # Create an account different from the auth account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        other_account = Account(
            id=AccountID(),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(other_account)

        # Superadmin should be able to access it
        response = await authenticated_client.get(f"/accounts/{other_account.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Other Account"

    async def test_superadmin_can_create_users_in_any_account(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can create users in any account."""
        # Create an account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        other_account = Account(
            id=AccountID(),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(other_account)

        # Create user in that account
        response = await authenticated_client.post(
            "/users",
            json={
                "account_id": str(other_account.id),
                "email": "user@other-account.com",
                "display_name": "Other User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "user@other-account.com"
        assert data["account_id"] == str(other_account.id)

    async def test_superadmin_can_manage_games_in_any_account(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can manage games in any account."""
        # Create an account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        other_account = Account(
            id=AccountID(),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(other_account)

        # Create game in that account
        response = await authenticated_client.post(
            "/games",
            json={
                "account_id": str(other_account.id),
                "name": "Test Game",
                "slug": "test-game",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Game"
        assert data["account_id"] == str(other_account.id)


@pytest.mark.asyncio
class TestRegularUserAuthorization:
    """Test suite for regular user access restrictions."""

    async def test_regular_user_cannot_create_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users cannot create accounts."""
        # Create a regular user (not superadmin) with API key
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account = Account(
            id=AccountID(),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create regular user
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="regular@user.com",
            display_name="Regular User",
            super_admin=False,  # NOT a superadmin
        )

        # Create API key for regular user
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name="Regular User Key",
        )

        # Try to create an account
        response = await client.post(
            "/accounts",
            json={
                "name": "New Account",
                "slug": "new-account",
            },
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "superadmin" in response.json()["detail"].lower()

    async def test_regular_user_can_only_see_own_account(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users only see their own account in list."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="User Account 1",
            slug="user-account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="User Account 2",
            slug="user-account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # List accounts
        response = await client.get(
            "/accounts",
            headers={"leadr-api-key": plain_key},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only see their own account
        assert len(data) == 1
        assert data[0]["id"] == str(account1.id)
        assert data[0]["name"] == "User Account 1"

    async def test_regular_user_cannot_access_other_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users get 403 when accessing other accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="User Account 1",
            slug="user-account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="User Account 2",
            slug="user-account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # Try to access account2
        response = await client.get(
            f"/accounts/{account2.id}",
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    async def test_regular_user_cannot_create_users_in_other_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users cannot create users in other accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="User Account 1",
            slug="user-account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="User Account 2",
            slug="user-account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # Try to create user in account2
        response = await client.post(
            "/users",
            json={
                "account_id": str(account2.id),
                "email": "newuser@account2.com",
                "display_name": "New User",
            },
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    async def test_regular_user_cannot_list_users_from_other_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users cannot list users from other accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="User Account 1",
            slug="user-account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="User Account 2",
            slug="user-account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # Try to list users from account2
        response = await client.get(
            f"/users?account_id={account2.id}",
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    async def test_regular_user_cannot_access_games_from_other_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users cannot access games from other accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="User Account 1",
            slug="user-account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="User Account 2",
            slug="user-account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create game in account2
        game_repo = GameRepository(db_session)
        game = Game(
            id=GameID(),
            account_id=account2.id,
            name="Account 2 Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # Try to access game from account2
        response = await client.get(
            f"/games/{game.id}",
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    async def test_regular_user_can_access_own_account_resources(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users CAN access their own account's resources."""
        # Create account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account = Account(
            id=AccountID(),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game in same account
        game_repo = GameRepository(db_session)
        game = Game(
            id=GameID(),
            account_id=account.id,
            name="My Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create user
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="user@test.com",
            display_name="User",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name="User Key",
        )

        # Access own account
        response = await client.get(
            f"/accounts/{account.id}",
            headers={"leadr-api-key": plain_key},
        )
        assert response.status_code == 200

        # Access own game
        response = await client.get(
            f"/games/{game.id}",
            headers={"leadr-api-key": plain_key},
        )
        assert response.status_code == 200

        # List own games
        response = await client.get(
            f"/games?account_id={account.id}",
            headers={"leadr-api-key": plain_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Game"


@pytest.mark.asyncio
class TestAPIKeyAuthorization:
    """Test suite for API key authorization across accounts."""

    async def test_regular_user_cannot_list_api_keys_from_other_accounts(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that users cannot list API keys from other accounts."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account 1",
            slug="account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account 2",
            slug="account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user1@test.com",
            display_name="User 1",
            super_admin=False,
        )

        # Create API key for user
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User 1 Key",
        )

        # Try to list API keys from account2
        response = await client.get(
            f"/api-keys?account_id={account2.id}",
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    async def test_superadmin_can_create_api_keys_for_any_account(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can create API keys for users in any account."""
        # Create another account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        other_account = Account(
            id=AccountID(),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(other_account)

        # Create user in that account
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=other_account.id,
            email="user@other.com",
            display_name="Other User",
        )

        # Superadmin creates API key for that user
        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(other_account.id),
                "user_id": str(user.id),
                "name": "Other User Key",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Other User Key"
        assert "key" in data


@pytest.mark.asyncio
class TestAccountIDResolution:
    """Test suite for automatic account_id resolution and validation."""

    async def test_regular_user_list_without_account_id_uses_their_account(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users can list resources without providing account_id.

        The account_id should be automatically derived from their API key's account.
        """
        # Create account and game
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account = Account(
            id=AccountID(uuid4()),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game = Game(
            id=GameID(uuid4()),
            account_id=account.id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create user
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="user@test.com",
            display_name="User",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name="User Key",
        )

        # List games WITHOUT providing account_id - should auto-derive
        response = await client.get(
            "/games",
            headers={"leadr-api-key": plain_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Game"

    async def test_superadmin_list_without_account_id_returns_400(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmins must provide account_id when listing resources."""
        # Try to list games without account_id
        response = await authenticated_client.get("/games")

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "must explicitly specify account_id" in response.json()["detail"]

    async def test_superadmin_list_with_account_id_succeeds(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmins can list resources when providing account_id."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account = Account(
            id=AccountID(uuid4()),
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game = Game(
            id=GameID(uuid4()),
            account_id=account.id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # List games WITH account_id
        response = await authenticated_client.get(f"/games?account_id={account.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Game"

    async def test_regular_user_list_with_wrong_account_id_returns_403(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users get 403 when providing different account_id in query."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(uuid4()),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(uuid4()),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user@test.com",
            display_name="User",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User Key",
        )

        # Try to list games with account2's ID
        response = await client.get(
            f"/games?account_id={account2.id}",
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    async def test_regular_user_create_with_wrong_account_id_returns_403(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users get 403 when providing different account_id in request body."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(uuid4()),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(uuid4()),
            name="Other Account",
            slug="other-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create user in account1
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="user@test.com",
            display_name="User",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user.id,
            name="User Key",
        )

        # Try to create a game with account2's ID in the request body
        response = await client.post(
            "/games",
            json={
                "account_id": str(account2.id),
                "name": "Test Game",
                "slug": "test-game",
            },
            headers={"leadr-api-key": plain_key},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    async def test_regular_user_list_users_without_account_id_succeeds(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """Test that regular users can list users without providing account_id."""
        # Create account
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account = Account(
            id=AccountID(uuid4()),
            name="User Account",
            slug="user-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        user_service = await get_user_service(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="user@test.com",
            display_name="User",
            super_admin=False,
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        _, plain_key = await api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name="User Key",
        )

        # List users WITHOUT providing account_id
        response = await client.get(
            "/users",
            headers={"leadr-api-key": plain_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(u["email"] == "user@test.com" for u in data)
