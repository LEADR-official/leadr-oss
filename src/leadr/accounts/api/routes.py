"""Account and User API routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

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
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.models import EntityID

router = APIRouter()


# Account routes
@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(request: AccountCreateRequest, db: DatabaseSession) -> AccountResponse:
    """Create a new account."""
    service = AccountService(db)
    now = datetime.now(UTC)

    account = await service.create_account(
        account_id=EntityID.generate(),
        name=request.name,
        slug=request.slug,
        created_at=now,
        updated_at=now,
    )

    return AccountResponse.from_domain(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, db: DatabaseSession) -> AccountResponse:
    """Get an account by ID."""
    service = AccountService(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID"
        ) from e

    account = await service.get_account(entity_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return AccountResponse.from_domain(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(db: DatabaseSession) -> list[AccountResponse]:
    """List all accounts."""
    service = AccountService(db)
    accounts = await service.list_accounts()
    return [AccountResponse.from_domain(acc) for acc in accounts]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str, request: AccountUpdateRequest, db: DatabaseSession
) -> AccountResponse:
    """Update an account."""
    service = AccountService(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID"
        ) from e

    try:
        # Handle soft delete first
        if request.deleted is True:
            account = await service.soft_delete(entity_id)
            return AccountResponse.from_domain(account)

        # Get account for updates
        account = await service.get_by_id_or_raise(entity_id)

        # Handle status changes using service methods
        if request.status == AccountStatus.SUSPENDED:
            account = await service.suspend_account(entity_id)
        elif request.status == AccountStatus.ACTIVE:
            account = await service.activate_account(entity_id)

        # Handle field updates using service method
        if request.name is not None or request.slug is not None:
            account = await service.update_account(
                entity_id,
                name=request.name,
                slug=request.slug,
            )

    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        ) from e

    return AccountResponse.from_domain(account)


# User routes
@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(request: UserCreateRequest, db: DatabaseSession) -> UserResponse:
    """Create a new user."""
    service = UserService(db)
    now = datetime.now(UTC)

    try:
        account_id = EntityID(value=request.account_id)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID"
        ) from e

    user = await service.create_user(
        account_id=account_id,
        email=request.email,
        display_name=request.display_name,
        created_at=now,
        updated_at=now,
    )

    return UserResponse.from_domain(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: DatabaseSession) -> UserResponse:
    """Get a user by ID."""
    service = UserService(db)

    try:
        entity_id = EntityID.from_string(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        ) from e

    user = await service.get_user(entity_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: DatabaseSession, account_id: Annotated[str | None, Query()] = None
) -> list[UserResponse]:
    """List users by account."""
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="account_id query parameter is required"
        )

    service = UserService(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID"
        ) from e

    users = await service.list_users_by_account(entity_id)
    return [UserResponse.from_domain(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, request: UserUpdateRequest, db: DatabaseSession
) -> UserResponse:
    """Update a user."""
    service = UserService(db)

    try:
        entity_id = EntityID.from_string(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        ) from e

    try:
        # Handle soft delete first
        if request.deleted is True:
            user = await service.get_user(entity_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            await service.delete_user(entity_id)
            return UserResponse.from_domain(user)

        # Update fields
        user = await service.update_user(
            user_id=entity_id,
            email=request.email,
            display_name=request.display_name,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from e

    return UserResponse.from_domain(user)
