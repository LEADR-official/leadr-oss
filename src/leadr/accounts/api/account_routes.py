"""Account API routes."""

from fastapi import APIRouter, HTTPException, status

from leadr.accounts.api.account_schemas import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from leadr.accounts.domain.account import AccountStatus
from leadr.accounts.services.dependencies import AccountServiceDep
from leadr.auth.dependencies import AuthContextDep
from leadr.common.domain.ids import AccountID

router = APIRouter()


@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(
    request: AccountCreateRequest,
    service: AccountServiceDep,
    auth: AuthContextDep,
) -> AccountResponse:
    """Create a new account.

    Only superadmins can create accounts.

    Args:
        request: Account creation details including name and slug.
        service: Injected account service dependency.
        auth: Authentication context with user info.

    Returns:
        AccountResponse with the created account including auto-generated ID and timestamps.

    Raises:
        403: User does not have permission to create accounts.
    """
    # Only superadmins can create accounts
    if not auth.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create accounts",
        )

    account = await service.create_account(
        name=request.name,
        slug=request.slug,
    )

    return AccountResponse.from_domain(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: AccountID,
    service: AccountServiceDep,
    auth: AuthContextDep,
) -> AccountResponse:
    """Get an account by ID.

    Args:
        account_id: Unique identifier for the account.
        service: Injected account service dependency.
        auth: Authentication context with user info.

    Returns:
        AccountResponse with full account details.

    Raises:
        403: User does not have access to this account.
        404: Account not found.
    """
    # Check authorization
    if not auth.has_access_to_account(account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this account",
        )

    account = await service.get_by_id_or_raise(account_id)
    return AccountResponse.from_domain(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    service: AccountServiceDep,
    auth: AuthContextDep,
) -> list[AccountResponse]:
    """List accounts.

    Superadmins see all accounts. Regular users see only their own account.

    Args:
        service: Injected account service dependency.
        auth: Authentication context with user info.

    Returns:
        List of accounts the user has access to.
    """
    if auth.is_superadmin:
        # Superadmins can see all accounts
        accounts = await service.list_accounts()
    else:
        # Regular users see only their own account
        account = await service.get_by_id_or_raise(auth.api_key.account_id)
        accounts = [account]

    return [AccountResponse.from_domain(acc) for acc in accounts]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: AccountID,
    request: AccountUpdateRequest,
    service: AccountServiceDep,
    auth: AuthContextDep,
) -> AccountResponse:
    """Update an account.

    Supports updating name, slug, status, or soft-deleting the account.
    Status changes (active/suspended) are handled through dedicated service methods.

    Args:
        account_id: Unique identifier for the account.
        request: Account update details (all fields optional).
        service: Injected account service dependency.
        auth: Authentication context with user info.

    Returns:
        AccountResponse with the updated account details.

    Raises:
        403: User does not have access to this account.
        404: Account not found.
    """
    # Check authorization
    if not auth.has_access_to_account(account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this account",
        )

    # Handle soft delete first
    if request.deleted is True:
        account = await service.soft_delete(account_id)
        return AccountResponse.from_domain(account)

    # Get account for updates
    account = await service.get_by_id_or_raise(account_id)

    # Handle status changes using service methods
    if request.status == AccountStatus.SUSPENDED:
        account = await service.suspend_account(account_id)
    elif request.status == AccountStatus.ACTIVE:
        account = await service.activate_account(account_id)

    # Handle field updates using service method
    if request.name is not None or request.slug is not None:
        account = await service.update_account(
            account_id,
            name=request.name,
            slug=request.slug,
        )

    return AccountResponse.from_domain(account)
