"""Account and User API routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError

from leadr.accounts.api.schemas import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from leadr.accounts.domain.account import AccountStatus
from leadr.accounts.services.dependencies import AccountServiceDep, UserServiceDep
from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)

router = APIRouter()


# Account routes
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
    account_id: UUID4,
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
    account_id: UUID4,
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


# User routes
@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    service: UserServiceDep,
    auth: AuthContextDep,
) -> UserResponse:
    """Create a new user.

    Creates a new user associated with an existing account.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: User creation details including account_id, email, and display name.
        service: Injected user service dependency.
        auth: Authentication context with user info.

    Returns:
        UserResponse with the created user including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Account not found.
    """
    validate_body_account_id(auth, request.account_id)

    try:
        user = await service.create_user(
            account_id=request.account_id,
            email=request.email,
            display_name=request.display_name,
        )
    except IntegrityError:
        # Foreign key constraint violation - account doesn't exist
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        ) from None

    return UserResponse.from_domain(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID4,
    service: UserServiceDep,
    auth: AuthContextDep,
) -> UserResponse:
    """Get a user by ID.

    Args:
        user_id: Unique identifier for the user.
        service: Injected user service dependency.
        auth: Authentication context with user info.

    Returns:
        UserResponse with full user details.

    Raises:
        403: User does not have access to this user's account.
        404: User not found.
    """
    user = await service.get_by_id_or_raise(user_id)

    # Check authorization - must have access to the user's account
    if not auth.has_access_to_account(user.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this user's account",
        )

    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    service: UserServiceDep,
    account_id: QueryAccountIDDep,
) -> list[UserResponse]:
    """List users for an account.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        service: Injected user service dependency.
        account_id: Account ID (auto-resolved for regular users, required for superadmins).

    Returns:
        List of users for the account.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    users = await service.list_users_by_account(account_id)
    return [UserResponse.from_domain(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID4,
    request: UserUpdateRequest,
    service: UserServiceDep,
    auth: AuthContextDep,
) -> UserResponse:
    """Update a user.

    Supports updating email, display name, or soft-deleting the user.

    Args:
        user_id: Unique identifier for the user.
        request: User update details (all fields optional).
        service: Injected user service dependency.
        auth: Authentication context with user info.

    Returns:
        UserResponse with the updated user details.

    Raises:
        403: User does not have access to this user's account.
        404: User not found.
    """
    # Fetch user to check authorization
    existing_user = await service.get_by_id_or_raise(user_id)

    # Check authorization - must have access to the user's account
    if not auth.has_access_to_account(existing_user.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this user's account",
        )

    # Handle soft delete first
    if request.deleted is True:
        user = await service.soft_delete(user_id)
        return UserResponse.from_domain(user)

    # Update fields
    user = await service.update_user(
        user_id=user_id,
        email=request.email,
        display_name=request.display_name,
        super_admin=request.super_admin,
    )

    return UserResponse.from_domain(user)
