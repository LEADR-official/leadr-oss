"""Account API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from leadr.accounts.api.account_schemas import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from leadr.accounts.domain.account import AccountStatus
from leadr.accounts.services.dependencies import AccountServiceDep
from leadr.auth.dependencies import AuthContextDep
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
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


@router.get("/accounts", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    service: AccountServiceDep,
    auth: AuthContextDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedResponse[AccountResponse]:
    """List accounts with pagination.

    Superadmins see all accounts (paginated). Regular users see only their own account.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, slug, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/accounts?limit=50&sort=name:asc

    Args:
        service: Injected account service dependency.
        auth: Authentication context with user info.
        pagination: Pagination parameters (cursor, limit, sort).

    Returns:
        PaginatedResponse with accounts and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
    """
    if auth.is_superadmin:
        # Superadmins can see all accounts (paginated)
        try:
            result = await service.list_accounts(pagination=pagination)
        except (CursorValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        return PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters={},
            response_model=AccountResponse,
        )
    else:
        # Regular users see only their own account (no pagination needed)
        account = await service.get_by_id_or_raise(auth.api_key.account_id)
        return PaginatedResponse(
            data=[AccountResponse.from_domain(account)],
            pagination=PaginationMeta(
                next_cursor=None,
                prev_cursor=None,
                has_next=False,
                has_prev=False,
                count=1,
            ),
        )


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
