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
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.user_service import UserService
from leadr.common.dependencies import DatabaseSession

router = APIRouter()


# Account routes
@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(request: AccountCreateRequest, db: DatabaseSession) -> AccountResponse:
    """Create a new account."""
    service = AccountService(db)

    account = await service.create_account(
        name=request.name,
        slug=request.slug,
    )

    return AccountResponse.from_domain(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID4, db: DatabaseSession) -> AccountResponse:
    """Get an account by ID."""
    service = AccountService(db)
    account = await service.get_by_id_or_raise(account_id)
    return AccountResponse.from_domain(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(db: DatabaseSession) -> list[AccountResponse]:
    """List all accounts."""
    service = AccountService(db)
    accounts = await service.list_accounts()
    return [AccountResponse.from_domain(acc) for acc in accounts]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID4, request: AccountUpdateRequest, db: DatabaseSession
) -> AccountResponse:
    """Update an account."""
    service = AccountService(db)

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
async def create_user(request: UserCreateRequest, db: DatabaseSession) -> UserResponse:
    """Create a new user.

    Raises:
        404: Account not found.
    """
    service = UserService(db)

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
async def get_user(user_id: UUID4, db: DatabaseSession) -> UserResponse:
    """Get a user by ID."""
    service = UserService(db)
    user = await service.get_by_id_or_raise(user_id)
    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: DatabaseSession,
    account_id: Annotated[UUID4, Query(description="Account ID to filter by")],
) -> list[UserResponse]:
    """List users for an account.

    TODO: Replace account_id query param with account_id from auth token.

    Args:
        account_id: Account ID to filter results (REQUIRED for multi-tenant safety).

    Returns:
        List of users for the account.
    """
    service = UserService(db)

    # TODO: Replace with account_id from authenticated user's token
    users = await service.list_users_by_account(account_id)
    return [UserResponse.from_domain(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID4, request: UserUpdateRequest, db: DatabaseSession
) -> UserResponse:
    """Update a user."""
    service = UserService(db)

    # Handle soft delete first
    if request.deleted is True:
        user = await service.soft_delete(user_id)
        return UserResponse.from_domain(user)

    # Update fields
    user = await service.update_user(
        user_id=user_id,
        email=request.email,
        display_name=request.display_name,
    )

    return UserResponse.from_domain(user)
