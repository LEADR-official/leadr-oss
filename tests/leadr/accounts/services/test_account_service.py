"""Tests for Account service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.account_service import AccountService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.mark.asyncio
class TestAccountService:
    """Test suite for Account service."""

    @pytest.fixture
    def service(self, mock_session):
        """Create AccountService with mocked repository."""
        mock_repo = MagicMock()
        return AccountService(mock_session, repository=mock_repo)

    async def test_create_account(self, service):
        """Test creating an account via service."""
        # Setup mocks
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)
        service.repository.get_by_slug = AsyncMock(return_value=None)  # slug doesn't exist

        account = await service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        assert account.id is not None
        assert account.name == "Acme Corporation"
        assert account.slug == "acme-corp"
        assert account.status == AccountStatus.ACTIVE
        service.repository.create.assert_called_once()

    async def test_get_account_by_id(self, service):
        """Test retrieving an account by ID via service."""
        # Create expected account
        account_id = AccountID()
        expected_account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )

        # Setup mock
        service.repository.get_by_id = AsyncMock(return_value=expected_account)

        # Retrieve it
        account = await service.get_account(account_id)

        assert account is not None
        assert account.id == account_id
        assert account.name == "Acme Corporation"
        service.repository.get_by_id.assert_called_once_with(account_id.uuid)

    async def test_get_account_by_id_not_found(self, service):
        """Test retrieving a non-existent account returns None."""
        non_existent_id = AccountID(uuid4())

        # Setup mock to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        account = await service.get_account(non_existent_id)

        assert account is None
        service.repository.get_by_id.assert_called_once_with(non_existent_id.uuid)

    async def test_get_account_by_slug(self, service):
        """Test retrieving an account by slug via service."""
        # Create expected account
        account_id = AccountID()
        expected_account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )

        # Setup mock
        service.repository.get_by_slug = AsyncMock(return_value=expected_account)

        # Retrieve by slug
        account = await service.get_account_by_slug("acme-corp")

        assert account is not None
        assert account.id == account_id
        assert account.slug == "acme-corp"
        service.repository.get_by_slug.assert_called_once_with("acme-corp")

    async def test_get_account_by_slug_not_found(self, service):
        """Test retrieving a non-existent account by slug returns None."""
        # Setup mock to return None
        service.repository.get_by_slug = AsyncMock(return_value=None)

        account = await service.get_account_by_slug("non-existent")

        assert account is None
        service.repository.get_by_slug.assert_called_once_with("non-existent")

    async def test_list_accounts(self, service):
        """Test listing all accounts via service."""
        # Create expected accounts
        account1 = Account(
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )
        account2 = Account(
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
        )

        # Create paginated result
        paginated_result = PaginatedResult(
            items=[account1, account2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Setup mock
        service.repository.filter = AsyncMock(return_value=paginated_result)

        # List them
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_accounts(pagination=pagination)

        assert len(result.items) == 2
        slugs = {acc.slug for acc in result.items}
        assert "acme-corp" in slugs
        assert "beta-industries" in slugs
        service.repository.filter.assert_called_once_with(pagination=pagination)

    async def test_suspend_account(self, service):
        """Test suspending an account via service."""
        # Create account
        account_id = AccountID()
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )

        # Setup mocks
        service.repository.get_by_id = AsyncMock(return_value=account)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Suspend it
        suspended_account = await service.suspend_account(account_id)

        assert suspended_account.status == AccountStatus.SUSPENDED
        service.repository.get_by_id.assert_called_once_with(account_id.uuid)
        service.repository.update.assert_called_once()

    async def test_suspend_account_not_found(self, service):
        """Test that suspending a non-existent account raises an error."""
        non_existent_id = AccountID(uuid4())

        # Setup mock to return None (account not found)
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.suspend_account(non_existent_id)

        assert "Account not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id.uuid)

    async def test_activate_account(self, service):
        """Test activating an account via service."""
        # Create suspended account
        account_id = AccountID()
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.SUSPENDED,
        )

        # Setup mocks
        service.repository.get_by_id = AsyncMock(return_value=account)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Activate it
        activated_account = await service.activate_account(account_id)

        assert activated_account.status == AccountStatus.ACTIVE
        service.repository.get_by_id.assert_called_once_with(account_id.uuid)
        service.repository.update.assert_called_once()

    async def test_activate_account_not_found(self, service):
        """Test that activating a non-existent account raises an error."""
        non_existent_id = AccountID(uuid4())

        # Setup mock to return None (account not found)
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.activate_account(non_existent_id)

        assert "Account not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id.uuid)

    async def test_delete_account(self, service):
        """Test soft-deleting an account via service."""
        # Create account
        account_id = AccountID()
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )

        # Setup mocks
        service.repository.get_by_id = AsyncMock(return_value=account)
        service.repository.delete = AsyncMock()

        # Delete it
        await service.delete_account(account_id)

        # Verify repository.delete was called
        service.repository.get_by_id.assert_called_once_with(account_id.uuid)
        service.repository.delete.assert_called_once_with(account_id.uuid)

    async def test_delete_account_not_found(self, service):
        """Test that deleting a non-existent account raises an error."""
        non_existent_id = AccountID(uuid4())

        # Setup mock to return None (account not found)
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.delete_account(non_existent_id)

        assert "Account not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id.uuid)

    async def test_delete_calls_repository_delete(self, service):
        """Test that delete_account correctly calls repository.delete."""
        # Create account
        account_id = AccountID()
        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
        )

        # Setup mocks
        service.repository.get_by_id = AsyncMock(return_value=account)
        service.repository.delete = AsyncMock()

        # Delete it
        await service.delete_account(account_id)

        # Verify repository.delete was called with correct ID
        service.repository.delete.assert_called_once_with(account_id.uuid)

    async def test_list_accounts_calls_repository_filter(self, service):
        """Test that list_accounts correctly calls repository.filter."""
        # Create paginated result
        paginated_result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Setup mock
        service.repository.filter = AsyncMock(return_value=paginated_result)

        # List accounts
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_accounts(pagination=pagination)

        # Verify repository.filter was called with correct pagination
        service.repository.filter.assert_called_once_with(pagination=pagination)
        assert result == paginated_result
