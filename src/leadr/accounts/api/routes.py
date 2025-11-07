"""Account and User API routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.common.dependencies import DatabaseSession
from leadr.common.domain.models import EntityID

router = APIRouter()


# Request/Response models for Accounts
class AccountCreateRequest(BaseModel):
    """Request model for creating an account."""

    name: str
    slug: str


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    name: str | None = None
    slug: str | None = None
    status: str | None = None


class AccountResponse(BaseModel):
    """Response model for an account."""

    id: str
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, account: Account) -> "AccountResponse":
        """Convert domain entity to response model."""
        return cls(
            id=str(account.id),
            name=account.name,
            slug=account.slug,
            status=account.status.value,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


# Request/Response models for Users
class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    account_id: str
    email: EmailStr
    display_name: str


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""

    email: EmailStr | None = None
    display_name: str | None = None


class UserResponse(BaseModel):
    """Response model for a user."""

    id: str
    account_id: str
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        """Convert domain entity to response model."""
        return cls(
            id=str(user.id),
            account_id=str(user.account_id),
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


# Account routes
@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(request: AccountCreateRequest, db: DatabaseSession) -> AccountResponse:
    """Create a new account."""
    repo = AccountRepository(db)

    now = datetime.now(UTC)
    account = Account(
        id=EntityID.generate(),
        name=request.name,
        slug=request.slug,
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    created = await repo.create(account)
    return AccountResponse.from_domain(created)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, db: DatabaseSession) -> AccountResponse:
    """Get an account by ID."""
    repo = AccountRepository(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID") from e

    account = await repo.get_by_id(entity_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return AccountResponse.from_domain(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(db: DatabaseSession) -> list[AccountResponse]:
    """List all accounts."""
    repo = AccountRepository(db)
    accounts = await repo.list_all()
    return [AccountResponse.from_domain(acc) for acc in accounts]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str, request: AccountUpdateRequest, db: DatabaseSession
) -> AccountResponse:
    """Update an account."""
    repo = AccountRepository(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID") from e

    account = await repo.get_by_id(entity_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Update fields if provided
    if request.name is not None:
        account.name = request.name
    if request.slug is not None:
        account.slug = request.slug
    if request.status is not None:
        account.status = AccountStatus(request.status)

    updated = await repo.update(account)
    return AccountResponse.from_domain(updated)


@router.post("/accounts/{account_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: str, db: DatabaseSession) -> None:
    """Soft-delete an account."""
    repo = AccountRepository(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID") from e

    # Check if account exists
    account = await repo.get_by_id(entity_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    await repo.delete(entity_id)


# User routes
@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(request: UserCreateRequest, db: DatabaseSession) -> UserResponse:
    """Create a new user."""
    repo = UserRepository(db)

    try:
        account_id = EntityID.from_string(request.account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID") from e

    now = datetime.now(UTC)
    user = User(
        id=EntityID.generate(),
        account_id=account_id,
        email=request.email,
        display_name=request.display_name,
        created_at=now,
        updated_at=now,
    )

    created = await repo.create(user)
    return UserResponse.from_domain(created)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: DatabaseSession) -> UserResponse:
    """Get a user by ID."""
    repo = UserRepository(db)

    try:
        entity_id = EntityID.from_string(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from e

    user = await repo.get_by_id(entity_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.from_domain(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    account_id: Annotated[str | None, Query()] = None, db: DatabaseSession = None
) -> list[UserResponse]:
    """List users by account."""
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="account_id query parameter is required"
        )

    repo = UserRepository(db)

    try:
        entity_id = EntityID.from_string(account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account ID") from e

    users = await repo.list_by_account(entity_id)
    return [UserResponse.from_domain(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, request: UserUpdateRequest, db: DatabaseSession) -> UserResponse:
    """Update a user."""
    repo = UserRepository(db)

    try:
        entity_id = EntityID.from_string(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from e

    user = await repo.get_by_id(entity_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update fields if provided
    if request.email is not None:
        user.email = request.email
    if request.display_name is not None:
        user.display_name = request.display_name

    updated = await repo.update(user)
    return UserResponse.from_domain(updated)


@router.post("/users/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: DatabaseSession) -> None:
    """Soft-delete a user."""
    repo = UserRepository(db)

    try:
        entity_id = EntityID.from_string(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from e

    # Check if user exists
    user = await repo.get_by_id(entity_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await repo.delete(entity_id)
