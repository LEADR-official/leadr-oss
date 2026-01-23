"""Identity service for player identity management."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.identity import Identity, IdentityKind, IdentitySession
from leadr.auth.services.device_token_crypto import (
    generate_access_token,
    generate_refresh_token,
    hash_token,
    validate_access_token,
    validate_refresh_token,
)
from leadr.auth.services.repositories import IdentityRepository, IdentitySessionRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.config import settings


class IdentityService(BaseService[Identity, IdentityRepository]):
    """Service for identity management and session handling."""

    def __init__(self, session: AsyncSession):
        """Initialize IdentityService.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        super().__init__(session)
        self.session_repo = IdentitySessionRepository(session)

    def _create_repository(self, session: AsyncSession) -> IdentityRepository:
        """Create repository instance."""
        return IdentityRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Identity"

    async def get_or_create_identity(
        self,
        account_id: AccountID,
        game_id: GameID,
        kind: IdentityKind,
        external_key: str,
        display_name: str | None = None,
    ) -> tuple[Identity, bool]:
        """Get an existing identity or create a new one.

        Args:
            account_id: Account ID
            game_id: Game ID
            kind: Identity kind (DEVICE, STEAM, CUSTOM)
            external_key: External identifier (e.g., device ID, Steam ID)
            display_name: Optional display name

        Returns:
            tuple[Identity, bool]: (identity, created) where created is True if new
        """
        # Try to find existing identity
        existing = await self.repository.get_by_external_key(
            account_id=account_id,
            game_id=game_id,
            kind=kind,
            external_key=external_key,
        )

        if existing:
            # Update display name if provided and different
            if display_name is not None and existing.display_name != display_name:
                existing.update_display_name(display_name)
                existing = await self.repository.update(existing)
            return existing, False

        # Create new identity
        identity = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=kind,
            external_key=external_key,
            display_name=display_name,
        )
        identity = await self.repository.create(identity)
        return identity, True

    async def get_identity(self, identity_id: IdentityID | UUID) -> Identity | None:
        """Get an identity by its ID.

        Args:
            identity_id: The ID of the identity to retrieve

        Returns:
            The identity if found, None otherwise
        """
        return await self.get_by_id(identity_id)

    async def get_identity_or_raise(self, identity_id: IdentityID | UUID) -> Identity:
        """Get an identity by its ID or raise EntityNotFoundError.

        Args:
            identity_id: The ID of the identity to retrieve

        Returns:
            The identity

        Raises:
            EntityNotFoundError: If the identity doesn't exist
        """
        return await self.get_by_id_or_raise(identity_id)

    async def list_identities(
        self,
        account_id: AccountID | None,
        *,
        game_id: GameID | None = None,
        kind: IdentityKind | None = None,
        pagination: PaginationParams,
    ) -> PaginatedResult[Identity]:
        """List identities for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all identities
                (superadmin use case).
            game_id: Optional game ID to filter by
            kind: Optional identity kind to filter by
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing Identity entities.
        """
        return await self.repository.filter(
            account_id=account_id,
            game_id=game_id,
            kind=kind,
            pagination=pagination,
        )

    async def update_identity(
        self,
        identity_id: IdentityID,
        display_name: str | None = None,
    ) -> Identity:
        """Update an identity's mutable fields.

        Args:
            identity_id: The ID of the identity to update
            display_name: New display name (None to clear)

        Returns:
            The updated identity

        Raises:
            EntityNotFoundError: If the identity doesn't exist
        """
        identity = await self.get_by_id_or_raise(identity_id)
        identity.update_display_name(display_name)
        return await self.repository.update(identity)

    async def start_session(
        self,
        identity: Identity,
        ip_address: str | None = None,
        user_agent: str | None = None,
        test_mode: bool = False,
    ) -> tuple[str, str, int]:
        """Start a new identity session.

        Creates a new session with access and refresh tokens.

        Args:
            identity: The identity to create a session for
            ip_address: Client IP address
            user_agent: Client user agent string
            test_mode: If True, session is in test mode

        Returns:
            tuple[str, str, int]: (access_token_plain, refresh_token_plain, expires_in_seconds)
        """
        # Generate access token
        access_expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRY_HOURS)
        access_token_plain, access_token_hash = generate_access_token(
            client_fingerprint=identity.external_key,  # Use external_key as subject
            game_id=identity.game_id,
            account_id=identity.account_id,
            expires_delta=access_expires_delta,
            secret=settings.JWT_SECRET,
            test_mode=test_mode,
            identity_id=identity.id,  # Include identity_id in token
        )

        # Generate refresh token
        refresh_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRY_DAYS)
        refresh_token_plain, refresh_token_hash = generate_refresh_token(
            client_fingerprint=identity.external_key,
            game_id=identity.game_id,
            account_id=identity.account_id,
            token_version=1,  # Initial version
            expires_delta=refresh_expires_delta,
            secret=settings.JWT_SECRET,
            test_mode=test_mode,
            identity_id=identity.id,  # Include identity_id in token
        )

        # Create session
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity.id,
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            token_version=1,
            expires_at=now + access_expires_delta,
            refresh_expires_at=now + refresh_expires_delta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.session_repo.create(session)

        expires_in_seconds = int(access_expires_delta.total_seconds())
        return access_token_plain, refresh_token_plain, expires_in_seconds

    async def validate_identity_token(self, token: str) -> Identity | None:
        """Validate access token and return associated identity.

        Validates JWT signature and expiration, checks session validity,
        and returns the identity.

        Args:
            token: JWT access token

        Returns:
            Identity if token is valid, None otherwise
        """
        # Validate JWT token
        claims = validate_access_token(token, settings.JWT_SECRET)
        if not claims:
            return None

        # Extract identity_id from claims
        identity_id_str = claims.get("identity_id")
        if not identity_id_str:
            return None

        identity_id = IdentityID(UUID(identity_id_str))

        # Get identity
        identity = await self.repository.get_by_id(identity_id)
        if not identity:
            return None

        # Verify session exists and is valid
        token_hash = hash_token(token, settings.JWT_SECRET)
        session = await self.session_repo.get_by_token_hash(token_hash)
        if not session:
            return None

        # Check session validity
        if not session.is_valid():
            return None

        return identity

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str, int] | None:
        """Refresh access token using a valid refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            tuple[str, str, int]: (access_token_plain, refresh_token_plain, expires_in_seconds)
            or None if refresh token is invalid
        """
        # Validate refresh JWT token
        claims = validate_refresh_token(refresh_token, settings.JWT_SECRET)
        if not claims:
            return None

        # Hash the refresh token and look up session
        refresh_token_hash = hash_token(refresh_token, settings.JWT_SECRET)
        session = await self.session_repo.get_by_refresh_token_hash(refresh_token_hash)
        if not session:
            return None

        # Verify token version matches (replay attack detection)
        jwt_version = claims["token_version"]
        if jwt_version != session.token_version:
            return None

        # Check that refresh token is not expired
        if session.is_refresh_expired():
            return None

        # Check that session is not revoked
        if session.is_revoked():
            return None

        # Get identity
        identity = await self.repository.get_by_id(session.identity_id)
        if not identity:
            return None

        # Extract claims for token generation
        test_mode = claims.get("test_mode", False)

        # Generate new access token
        access_expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRY_HOURS)
        access_token_plain, access_token_hash = generate_access_token(
            client_fingerprint=identity.external_key,
            game_id=identity.game_id,
            account_id=identity.account_id,
            expires_delta=access_expires_delta,
            secret=settings.JWT_SECRET,
            test_mode=test_mode,
            identity_id=identity.id,
        )

        # Generate new refresh token with incremented version
        refresh_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRY_DAYS)
        new_refresh_token_plain, new_refresh_token_hash = generate_refresh_token(
            client_fingerprint=identity.external_key,
            game_id=identity.game_id,
            account_id=identity.account_id,
            token_version=session.token_version + 1,
            expires_delta=refresh_expires_delta,
            secret=settings.JWT_SECRET,
            test_mode=test_mode,
            identity_id=identity.id,
        )

        # Update session with new tokens and incremented version
        session.access_token_hash = access_token_hash
        session.refresh_token_hash = new_refresh_token_hash
        session.rotate_tokens()  # Increments token_version
        session.expires_at = datetime.now(UTC) + access_expires_delta
        session.refresh_expires_at = datetime.now(UTC) + refresh_expires_delta
        await self.session_repo.update(session)

        expires_in_seconds = int(access_expires_delta.total_seconds())
        return access_token_plain, new_refresh_token_plain, expires_in_seconds

    async def list_sessions(
        self,
        account_id: AccountID | None,
        *,
        identity_id: IdentityID | None = None,
        pagination: PaginationParams,
    ) -> PaginatedResult[IdentitySession]:
        """List identity sessions with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all sessions
                (superadmin use case).
            identity_id: Optional identity ID to filter by
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing IdentitySession entities.
        """
        return await self.session_repo.filter(
            account_id=account_id,
            identity_id=identity_id,
            pagination=pagination,
        )

    async def get_session(self, session_id: IdentitySessionID | UUID) -> IdentitySession | None:
        """Get an identity session by its ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            The session if found, None otherwise
        """
        return await self.session_repo.get_by_id(session_id)

    async def get_session_or_raise(self, session_id: IdentitySessionID) -> IdentitySession:
        """Get an identity session by its ID or raise EntityNotFoundError.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            The session

        Raises:
            EntityNotFoundError: If the session doesn't exist
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError("IdentitySession", str(session_id))
        return session

    async def revoke_session(self, session_id: IdentitySessionID) -> IdentitySession:
        """Revoke an identity session.

        Args:
            session_id: The ID of the session to revoke

        Returns:
            The updated session

        Raises:
            EntityNotFoundError: If the session doesn't exist
        """
        session = await self.get_session_or_raise(session_id)
        session.revoke()
        return await self.session_repo.update(session)
