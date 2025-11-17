"""User API routes."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.accounts.api.user_schemas import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from leadr.accounts.services.dependencies import UserServiceDep
from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.common.domain.ids import UserID

router = APIRouter()


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
    user_id: UserID,
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
    user_id: UserID,
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
