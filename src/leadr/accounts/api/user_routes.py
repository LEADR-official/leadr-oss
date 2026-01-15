"""User API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.accounts.api.user_schemas import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from leadr.accounts.domain.user import UserStatus
from leadr.accounts.services.dependencies import UserServiceDep
from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, UserID

router = APIRouter()


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    service: UserServiceDep,
    auth: AdminAuthContextDep,
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
    auth: AdminAuthContextDep,
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


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    auth: AdminAuthContextDep,
    service: UserServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
) -> PaginatedResponse[UserResponse]:
    """List users for an account with pagination.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns users from all accounts.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=email:asc,created_at:desc
    - Valid sort fields: id, email, display_name, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/users?account_id=acc_123&limit=50&sort=email:asc

    Args:
        auth: Authentication context with user info.
        service: Injected user service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).

    Returns:
        PaginatedResponse with users and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    try:
        result = await service.list_users_by_account(effective_account_id, pagination=pagination)
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters={},
        response_model=UserResponse,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UserID,
    request: UserUpdateRequest,
    service: UserServiceDep,
    auth: AdminAuthContextDep,
) -> UserResponse:
    """Update a user.

    Supports updating email, display name, status, or soft-deleting the user.
    Status changes (active/suspended) are handled through dedicated service methods.

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

    # Handle status changes using dedicated service methods
    user = existing_user
    if request.status == UserStatus.SUSPENDED:
        user = await service.suspend_user(user_id)
    elif request.status == UserStatus.ACTIVE:
        user = await service.activate_user(user_id)

    # Get only fields explicitly provided in request (exclude_unset=True)
    # This allows null values to clear fields vs omitted fields staying unchanged
    update_data = request.model_dump(exclude_unset=True)
    update_data.pop("deleted", None)  # Handled separately above
    update_data.pop("status", None)  # Handled separately above

    if update_data:
        user = await service.update_user(user_id, **update_data)

    return UserResponse.from_domain(user)
