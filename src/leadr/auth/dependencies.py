"""Authentication dependencies for FastAPI."""

import json
import logging
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, Header, HTTPException, Query, Request

from leadr.accounts.domain.user import User
from leadr.accounts.services.dependencies import UserServiceDep
from leadr.auth.domain.api_key import APIKey
from leadr.auth.domain.identity import Identity
from leadr.auth.services.dependencies import (
    APIKeyServiceDep,
    IdentityServiceDep,
    NonceServiceDep,
)
from leadr.auth.services.device_token_crypto import validate_access_token
from leadr.common.domain.ids import AccountID, GameID
from leadr.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthContext:
    """Unified authentication context for both admin and client auth.

    This context provides a unified interface for both API key (admin) and
    identity token (client) authentication. It includes helper methods for
    authorization checks that work transparently across both auth types.

    Attributes:
        account_id: The account ID associated with this auth context.
        user: The user entity (present for admin auth only).
        api_key: The API key entity (present for admin auth only).
        identity: The identity entity (present for client auth only).
    """

    account_id: AccountID
    user: User | None = None
    api_key: APIKey | None = None
    identity: Identity | None = None

    @property
    def auth_type(self) -> Literal["admin", "client"]:
        """Return the authentication type.

        Returns:
            "admin" if authenticated via API key, "client" if via identity token.
        """
        if self.api_key is not None:
            return "admin"
        elif self.identity is not None:
            return "client"
        else:
            raise ValueError("Neither api_key nor identity set for AuthContext")

    @property
    def is_superadmin(self) -> bool:
        """Check if the authenticated user has superadmin privileges.

        Only applies to admin auth. Client auth never has superadmin privileges.

        Returns:
            True if user is a superadmin, False otherwise.
        """
        return self.user is not None and self.user.super_admin

    def has_access_to_account(self, account_id: AccountID) -> bool:
        """Check if the authenticated context has access to a specific account.

        For admin auth:
            - Superadmins have access to all accounts
            - Regular users only have access to their own account

        For client auth:
            - Identities only have access to their game's account

        Args:
            account_id: The account ID to check access for.

        Returns:
            True if context has access to the account, False otherwise.
        """
        if self.auth_type == "admin":
            return self.is_superadmin or self.account_id == account_id
        else:  # client
            return self.account_id == account_id


class AdminAuthContext(AuthContext):
    """Admin authentication context with guaranteed user and api_key fields.

    This subclass is returned by admin-only authentication dependencies,
    providing type-safe access to user and api_key without None checks.

    Note: This class does not use @dataclass to avoid conflicts between
    frozen dataclass fields and property overrides.

    Attributes:
        account_id: The account ID for this request (may differ from API key's
            account for superadmins).
        user: The authenticated user (guaranteed non-None).
        api_key: The authenticated API key (guaranteed non-None).
        identity: Always None for admin auth.
    """

    def __init__(
        self,
        account_id: AccountID,
        user: User,
        api_key: APIKey,
        identity: None = None,
    ):
        """Create admin auth context with guaranteed non-None user and api_key."""
        # Use private attributes to avoid property override conflicts
        object.__setattr__(self, "_account_id", account_id)
        object.__setattr__(self, "_user", user)
        object.__setattr__(self, "_api_key", api_key)
        object.__setattr__(self, "_identity", identity)

    @property  # type: ignore[override]
    def account_id(self) -> AccountID:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get account ID."""
        return self._account_id  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def user(self) -> User:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get user (guaranteed non-None for admin auth)."""
        return self._user  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def api_key(self) -> APIKey:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get API key (guaranteed non-None for admin auth)."""
        return self._api_key  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def identity(self) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get identity (always None for admin auth)."""
        return self._identity  # type: ignore[attr-defined]


class ClientAuthContext(AuthContext):
    """Client authentication context with guaranteed identity field.

    This subclass is returned by client-only authentication dependencies,
    providing type-safe access to identity without None checks.

    Note: This class does not use @dataclass to avoid conflicts between
    frozen dataclass fields and property overrides.

    Attributes:
        account_id: The account ID from the identity's game.
        identity: The player identity (guaranteed non-None).
        user: Always None for client auth.
        api_key: Always None for client auth.
        test_mode: Whether this session is in test mode.
    """

    def __init__(
        self,
        account_id: AccountID,
        identity: Identity,
        user: None = None,
        api_key: None = None,
        test_mode: bool = False,
    ):
        """Create client auth context with guaranteed non-None identity."""
        # Use private attributes to avoid property override conflicts
        object.__setattr__(self, "_account_id", account_id)
        object.__setattr__(self, "_user", user)
        object.__setattr__(self, "_api_key", api_key)
        object.__setattr__(self, "_identity", identity)
        object.__setattr__(self, "_test_mode", test_mode)

    @property  # type: ignore[override]
    def account_id(self) -> AccountID:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get account ID."""
        return self._account_id  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def user(self) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get user (always None for client auth)."""
        return self._user  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def api_key(self) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get API key (always None for client auth)."""
        return self._api_key  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def identity(self) -> Identity:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Get identity (guaranteed non-None for client auth)."""
        return self._identity  # type: ignore[attr-defined]

    @property
    def game_id(self) -> GameID:
        """Get game ID from identity (convenience property)."""
        return self._identity.game_id  # type: ignore[attr-defined]

    @property
    def test_mode(self) -> bool:
        """Get test_mode flag (whether session is in test mode)."""
        return self._test_mode  # type: ignore[attr-defined]


class AuthContextDependency:
    """Parameterizable authentication dependency using FastAPI class instance pattern.

    This class implements the callable instance pattern to provide flexible
    authentication requirements. Create instances with different parameters
    to require different auth types.

    Examples:
        >>> require_admin_auth = AuthContextDependency(require_admin=True)
        >>> require_client_auth = AuthContextDependency(require_client=True)
        >>> require_either_auth = AuthContextDependency(require_admin=True, require_client=True)
        >>>
        >>> @router.get("/admin-only")
        >>> async def admin_endpoint(
        >>>     auth: Annotated[AuthContext, Depends(require_admin_auth)]
        >>> ):
        >>>     return {"account": auth.account_id}
    """

    def __init__(
        self,
        require_admin: bool = False,
        require_client: bool = False,
        require_nonce: bool = False,
        require_superadmin_account_id: bool = False,
        require_superadmin: bool = False,
    ):
        """Initialize authentication requirements.

        Args:
            require_admin: If True, admin API key authentication is required.
            require_client: If True, client device token authentication is required.
            require_nonce: If True, nonce validation is required for client auth (mutations).
            require_superadmin_account_id: If True, superadmins must provide account_id
                query parameter on GET requests. Used for list endpoints.
            require_superadmin: If True, only superadmin users are allowed. Returns 403
                for non-superadmin users. Implies require_admin=True.

        Raises:
            ValueError: If neither require_admin nor require_client is True.
        """
        # require_superadmin implies require_admin
        if require_superadmin:
            require_admin = True

        if not require_admin and not require_client:
            raise ValueError("At least one of require_admin or require_client must be True")

        self.require_admin = require_admin
        self.require_client = require_client
        self.require_nonce = require_nonce
        self.require_superadmin_account_id = require_superadmin_account_id
        self.require_superadmin = require_superadmin

    async def __call__(
        self,
        request: Request,
        api_key_service: APIKeyServiceDep,
        user_service: UserServiceDep,
        identity_service: IdentityServiceDep,
        nonce_service: NonceServiceDep,
        background_tasks: BackgroundTasks,
        query_account_id: Annotated[AccountID | None, Query(alias="account_id")] = None,
        api_key: Annotated[str | None, Header(alias="leadr-api-key")] = None,
        authorization: Annotated[str | None, Header()] = None,
        leadr_client_nonce: Annotated[str | None, Header(alias="leadr-client-nonce")] = None,
    ) -> AdminAuthContext | ClientAuthContext | AuthContext:
        """Validate authentication and return AuthContext.

        This method is called by FastAPI's dependency injection system. It checks
        the enabled API flags, validates the appropriate authentication method(s),
        and returns a unified AuthContext.

        Args:
            request: The FastAPI request object.
            api_key_service: API key service dependency.
            user_service: User service dependency.
            identity_service: Identity service dependency.
            nonce_service: Nonce service dependency.
            query_account_id: Optional account_id from query parameters.
            api_key: The API key from 'leadr-api-key' header.
            authorization: The Authorization header (Bearer token).
            leadr_client_nonce: The nonce from 'leadr-client-nonce' header.

        Returns:
            AdminAuthContext if admin-only auth.
            ClientAuthContext if client-only auth.
            AuthContext (base class) if OR logic used (both auth types required).

        Raises:
            HTTPException: 401 if auth is disabled, missing, or invalid.
            HTTPException: 500 if server is misconfigured.
        """
        # Extract account_id from request body if present (for POST/PATCH/PUT requests)
        # Uses Starlette's cached body - safe to call multiple times
        body_account_id = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_data = json.loads(body_bytes)
                    if isinstance(body_data, dict) and "account_id" in body_data:
                        body_account_id = AccountID(body_data["account_id"])
            except (json.JSONDecodeError, ValueError, KeyError):
                # Ignore parsing errors - let Pydantic validate the body
                pass

        # Admin-only authentication
        if self.require_admin and not self.require_client:
            if not settings.ENABLE_ADMIN_API:
                logger.exception(
                    "Server misconfigured: endpoint requires admin auth but "
                    "ENABLE_ADMIN_API is False"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Admin API is not enabled",
                )
            if not api_key:
                logger.debug("Request requires admin API key auth but none was provided.")
                raise HTTPException(
                    status_code=401,
                    detail="API key required",
                )
            auth_context = await self._validate_admin_auth(
                api_key=api_key,
                api_key_service=api_key_service,
                user_service=user_service,
                request=request,
                background_tasks=background_tasks,
            )

            # Check superadmin requirement
            if self.require_superadmin and not auth_context.is_superadmin:
                raise HTTPException(
                    status_code=403,
                    detail="Superadmin access required",
                )

            # Check access if an account_id was provided
            account_id_to_check = body_account_id or query_account_id
            if account_id_to_check and not auth_context.has_access_to_account(account_id_to_check):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to the specified account",
                )
            return auth_context

        # Client-only authentication
        if self.require_client and not self.require_admin:
            if not settings.ENABLE_CLIENT_API:
                logger.exception(
                    "Server misconfigured: endpoint requires client auth but "
                    "ENABLE_CLIENT_API is False"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Client API is not enabled",
                )
            if not authorization:
                logger.debug("Request requires client API bearer token auth but none was provided.")
                raise HTTPException(
                    status_code=401,
                    detail="Authorization token required",
                )
            return await self._validate_client_auth(
                authorization=authorization,
                identity_service=identity_service,
                nonce_service=nonce_service,
                leadr_client_nonce=leadr_client_nonce,
            )

        # Should never reach here due to __init__ validation
        raise ValueError("At least one of require_admin or require_client must be True")

    async def _validate_admin_auth(
        self,
        api_key: str,
        api_key_service: APIKeyServiceDep,
        user_service: UserServiceDep,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> AdminAuthContext:
        """Validate admin API key authentication.

        Validates the API key and fetches the associated user in a single JOIN
        query for optimal performance. Schedules a background task to update
        last_used_at if the key hasn't been used recently (based on
        API_KEY_USAGE_UPDATE_THRESHOLD_SECONDS).

        Args:
            api_key: The API key string.
            api_key_service: API key service for validation.
            user_service: User service (unused - kept for signature compatibility).
            request: FastAPI request object for checking HTTP method.
            background_tasks: FastAPI BackgroundTasks for scheduling async work.

        Returns:
            AdminAuthContext with guaranteed user and api_key fields.

        Raises:
            HTTPException: 401 if API key is invalid or user not found.
        """
        # Validate API key and fetch user in a single JOIN query
        result = await api_key_service.validate_api_key_with_user(api_key)

        if result is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key",
            )

        validated_key, user = result

        # Schedule background update of last_used_at if stale
        if api_key_service.should_update_usage(validated_key):
            background_tasks.add_task(
                api_key_service.record_usage_async,
                validated_key.id,
            )

        return AdminAuthContext(
            account_id=validated_key.account_id,
            user=user,
            api_key=validated_key,
            identity=None,
        )

    async def _validate_client_auth(
        self,
        authorization: str,
        identity_service: IdentityServiceDep,
        nonce_service: NonceServiceDep,
        leadr_client_nonce: str | None,
    ) -> ClientAuthContext:
        """Validate client identity token authentication.

        Validates the bearer token, resolves the identity, and optionally validates
        nonce for mutations.

        Args:
            authorization: The Authorization header value.
            identity_service: Identity service for token validation.
            nonce_service: Nonce service for nonce validation.
            leadr_client_nonce: The nonce header value (required if require_nonce=True).

        Returns:
            ClientAuthContext with guaranteed identity field.

        Raises:
            HTTPException: 401 if token is invalid or malformed.
            HTTPException: 412 if nonce is required but missing/invalid.
        """
        if settings.DEBUG:
            logger.debug("Authorization: %s", authorization)

        # Parse Bearer token
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization format. Expected 'Bearer <token>'",
            )

        token = parts[1]

        # Validate identity token via IdentityService
        identity = await identity_service.validate_identity_token(token)

        if identity is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

        # Extract test_mode from JWT claims
        claims = validate_access_token(token, settings.JWT_SECRET)
        test_mode = claims.get("test_mode", False) if claims else False

        # Validate nonce if required (for mutations)
        if self.require_nonce:
            if leadr_client_nonce is None:
                raise HTTPException(
                    status_code=412,
                    detail="Nonce required",
                )

            try:
                await nonce_service.validate_and_consume_nonce(
                    nonce_value=leadr_client_nonce,
                    identity_id=identity.id,
                )
            except ValueError as e:
                error_msg = str(e).lower()

                if "not found" in error_msg:
                    detail = "Invalid nonce"
                elif "does not belong" in error_msg:
                    detail = "Nonce does not belong to this identity"
                elif "already used" in error_msg:
                    detail = "Nonce already used"
                elif "expired" in error_msg:
                    detail = "Nonce expired"
                else:
                    detail = "Invalid nonce"

                raise HTTPException(
                    status_code=412,
                    detail=detail,
                ) from None

        return ClientAuthContext(
            account_id=identity.account_id,
            identity=identity,
            test_mode=test_mode,
        )


# Create dependency instances for common use cases
require_admin_auth = AuthContextDependency(require_admin=True)
require_admin_auth_with_account_id = AuthContextDependency(
    require_admin=True, require_superadmin_account_id=True
)
require_superadmin_auth = AuthContextDependency(require_superadmin=True)
require_client_auth = AuthContextDependency(require_client=True)
require_client_auth_with_nonce = AuthContextDependency(require_client=True, require_nonce=True)

# Type aliases for dependency injection with specific return types
AdminAuthContextDep = Annotated[AdminAuthContext, Depends(require_admin_auth)]
AdminAuthContextWithAccountIDDep = Annotated[
    AdminAuthContext, Depends(require_admin_auth_with_account_id)
]
SuperAdminAuthContextDep = Annotated[AdminAuthContext, Depends(require_superadmin_auth)]
ClientAuthContextDep = Annotated[ClientAuthContext, Depends(require_client_auth)]
ClientAuthContextWithNonceDep = Annotated[
    ClientAuthContext, Depends(require_client_auth_with_nonce)
]
