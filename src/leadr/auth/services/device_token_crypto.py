"""Cryptographic operations for device access and refresh tokens."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt

from leadr.common.domain.ids import AccountID, GameID


def generate_access_token(
    device_id: str,
    game_id: GameID,
    account_id: AccountID,
    expires_delta: timedelta,
    secret: str,
) -> tuple[str, str]:
    """Generate JWT access token for device authentication.

    Creates a JWT with device, game, and account claims, signs it with the secret,
    and returns both the plain token and its SHA-256 hash for storage.

    Args:
        device_id: Client-generated device identifier
        game_id: Game UUID
        account_id: Account UUID (for multi-tenant isolation)
        expires_delta: Time until token expires
        secret: Server-side secret for JWT signing

    Returns:
        tuple[str, str]: (token_plain, token_hash)
            - token_plain: JWT access token to return to client
            - token_hash: SHA-256 hash for secure storage

    Example:
        >>> device_id = "device-123"
        >>> game_id = UUID("...")
        >>> account_id = UUID("...")
        >>> token, token_hash = generate_access_token(
        ...     device_id, game_id, account_id, timedelta(hours=1), "secret"
        ... )
        >>> token.count(".")
        2
    """
    now = datetime.now(UTC)
    exp = now + expires_delta

    payload = {
        "sub": device_id,  # Subject: device_id
        "game_id": str(game_id.uuid),
        "account_id": str(account_id.uuid),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid4()),  # Unique token ID
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    token_hash = hash_token(token, secret)

    return token, token_hash


def validate_access_token(token: str, secret: str) -> dict[str, Any] | None:
    """Validate and decode JWT access token.

    Verifies the token signature and expiration. Returns decoded claims if valid.

    Args:
        token: JWT access token to validate
        secret: Server-side secret for JWT verification

    Returns:
        dict with claims (sub, game_id, account_id, exp, iat, jti) or None if invalid

    Example:
        >>> token = "eyJ..."
        >>> claims = validate_access_token(token, "secret")
        >>> claims["sub"] if claims else None
        'device-123'
    """
    try:
        # Decode and verify signature and expiration
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "game_id", "account_id", "exp", "iat", "jti"]},
        )
        return claims
    except jwt.InvalidTokenError:
        # Covers ExpiredSignatureError, DecodeError, InvalidSignatureError, etc.
        return None


def generate_refresh_token(
    device_id: str,
    game_id: GameID,
    account_id: AccountID,
    token_version: int,
    expires_delta: timedelta,
    secret: str,
) -> tuple[str, str]:
    """Generate JWT refresh token for device authentication.

    Creates a JWT with device, game, account, and version claims, signs it with the secret,
    and returns both the plain token and its SHA-256 hash for storage.

    The token_version claim enables token rotation: when a refresh token is used,
    the version is incremented and old tokens with lower versions are invalidated.

    Args:
        device_id: Client-generated device identifier
        game_id: Game UUID
        account_id: Account UUID (for multi-tenant isolation)
        token_version: Current token version for rotation tracking
        expires_delta: Time until token expires (typically 30 days)
        secret: Server-side secret for JWT signing

    Returns:
        tuple[str, str]: (token_plain, token_hash)
            - token_plain: JWT refresh token to return to client
            - token_hash: SHA-256 hash for secure storage

    Example:
        >>> device_id = "device-123"
        >>> game_id = UUID("...")
        >>> account_id = UUID("...")
        >>> token, token_hash = generate_refresh_token(
        ...     device_id, game_id, account_id, 1, timedelta(days=30), "secret"
        ... )
        >>> token.count(".")
        2
    """
    now = datetime.now(UTC)
    exp = now + expires_delta

    payload = {
        "sub": device_id,  # Subject: device_id
        "game_id": str(game_id.uuid),
        "account_id": str(account_id.uuid),
        "token_version": token_version,  # For token rotation
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid4()),  # Unique token ID
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    token_hash = hash_token(token, secret)

    return token, token_hash


def validate_refresh_token(token: str, secret: str) -> dict[str, Any] | None:
    """Validate and decode JWT refresh token.

    Verifies the token signature and expiration. Returns decoded claims if valid.

    Args:
        token: JWT refresh token to validate
        secret: Server-side secret for JWT verification

    Returns:
        dict with claims (sub, game_id, account_id, token_version, exp, iat, jti) or None if invalid

    Example:
        >>> token = "eyJ..."
        >>> claims = validate_refresh_token(token, "secret")
        >>> claims["token_version"] if claims else None
        1
    """
    try:
        # Decode and verify signature and expiration
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={
                "require": ["sub", "game_id", "account_id", "token_version", "exp", "iat", "jti"]
            },
        )
        return claims
    except jwt.InvalidTokenError:
        # Covers ExpiredSignatureError, DecodeError, InvalidSignatureError, etc.
        return None


def hash_token(token: str, secret: str) -> str:
    """Hash token for secure storage using HMAC-SHA256.

    Uses HMAC-SHA256 with a server-side secret (pepper) to create
    a one-way hash of the token. This provides defense in depth:
    database compromise alone isn't enough to use tokens.

    Args:
        token: The JWT token to hash
        secret: Server-side secret for additional security

    Returns:
        A hexadecimal string representation of the HMAC-SHA256 hash

    Example:
        >>> secret = "my-secret"
        >>> hash1 = hash_token("token123", secret)
        >>> hash2 = hash_token("token123", secret)
        >>> hash1 == hash2
        True
        >>> len(hash1)
        64
    """
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
