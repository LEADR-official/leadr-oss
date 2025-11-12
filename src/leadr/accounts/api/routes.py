"""Account and User API routes."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
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

router = APIRouter()


# Account routes
@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(
    request: AccountCreateRequest, service: AccountServiceDep
) -> AccountResponse:
    """Create a new account.

    Args:
        request: Account creation details including name and slug.
        service: Injected account service dependency.

    Returns:
        AccountResponse with the created account including auto-generated ID and timestamps.
    """
    account = await service.create_account(
        name=request.name,
        slug=request.slug,
    )

    return AccountResponse.from_domain(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID4, service: AccountServiceDep) -> AccountResponse:
    """Get an account by ID.

    Args:
        account_id: Unique identifier for the account.
        service: Injected account service dependency.

    Returns:
        AccountResponse with full account details.

    Raises:
        404: Account not found.
    """
    account = await service.get_by_id_or_raise(account_id)
    return AccountResponse.from_domain(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(service: AccountServiceDep) -> list[AccountResponse]:
    """List all accounts.

    Args:
        service: Injected account service dependency.

    Returns:
        List of all active accounts.
    """
    accounts = await service.list_accounts()
    return [AccountResponse.from_domain(acc) for acc in accounts]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID4, request: AccountUpdateRequest, service: AccountServiceDep
) -> AccountResponse:
    """Update an account.

    Supports updating name, slug, status, or soft-deleting the account.
    Status changes (active/suspended) are handled through dedicated service methods.

    Args:
        account_id: Unique identifier for the account.
        request: Account update details (all fields optional).
        service: Injected account service dependency.

    Returns:
        AccountResponse with the updated account details.

    Raises:
        404: Account not found.
    """

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
async def create_user(request: UserCreateRequest, service: UserServiceDep) -> UserResponse:
    """Create a new user.

    Creates a new user associated with an existing account.

    Args:
        request: User creation details including account_id, email, and display name.
        service: Injected user service dependency.

    Returns:
        UserResponse with the created user including auto-generated ID and timestamps.

    Raises:
        404: Account not found.
    """
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
async def get_user(user_id: UUID4, service: UserServiceDep) -> UserResponse:
    """Get a user by ID.

    Args:
        user_id: Unique identifier for the user.
        service: Injected user service dependency.

    Returns:
        UserResponse with full user details.

    Raises:
        404: User not found.
    """
    user = await service.get_by_id_or_raise(user_id)
    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    service: UserServiceDep,
    account_id: Annotated[UUID4, Query(description="Account ID to filter by")],
) -> list[UserResponse]:
    """List users for an account.

    TODO: Replace account_id query param with account_id from auth token.

    Args:
        service: Injected user service dependency.
        account_id: Account ID to filter results (REQUIRED for multi-tenant safety).

    Returns:
        List of users for the account.
    """
    # TODO: Replace with account_id from authenticated user's token
    users = await service.list_users_by_account(account_id)
    return [UserResponse.from_domain(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID4, request: UserUpdateRequest, service: UserServiceDep
) -> UserResponse:
    """Update a user.

    Supports updating email, display name, or soft-deleting the user.

    Args:
        user_id: Unique identifier for the user.
        request: User update details (all fields optional).
        service: Injected user service dependency.

    Returns:
        UserResponse with the updated user details.

    Raises:
        404: User not found.
    """

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
