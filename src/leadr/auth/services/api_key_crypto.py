"""Cryptographic operations for API keys."""

import hmac
import secrets
from base64 import urlsafe_b64encode

API_KEY_PREFIX = "ldr_"
API_KEY_BYTES = 32  # 256 bits of entropy


def generate_api_key() -> str:
    """Generate a secure random API key with 'ldr_' prefix.

    The key is generated using cryptographically secure random bytes
    and encoded using URL-safe base64 encoding for compatibility.

    Returns:
        A secure API key string starting with 'ldr_' followed by
        URL-safe random characters (alphanumeric, hyphen, underscore).

    Example:
        >>> key = generate_api_key()
        >>> key.startswith('ldr_')
        True
        >>> len(key) > 36
        True
    """
    random_bytes = secrets.token_bytes(API_KEY_BYTES)
    # Use urlsafe_b64encode and strip padding for clean keys
    encoded = urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")
    return f"{API_KEY_PREFIX}{encoded}"


def hash_api_key(key: str, secret: str) -> str:
    """Hash an API key for secure storage using HMAC-SHA256.

    Uses HMAC-SHA256 with a server-side secret (pepper) to create
    a one-way hash of the API key. This provides defense in depth:
    database compromise alone isn't enough to validate keys.

    Args:
        key: The API key to hash.
        secret: Server-side secret for additional security.

    Returns:
        A hexadecimal string representation of the HMAC-SHA256 hash.

    Example:
        >>> secret = "my-secret"
        >>> hash1 = hash_api_key('ldr_test123', secret)
        >>> hash2 = hash_api_key('ldr_test123', secret)
        >>> hash1 == hash2
        True
        >>> len(hash1)
        64
    """
    return hmac.new(
        secret.encode("utf-8"),
        key.encode("utf-8"),
        "sha256",
    ).hexdigest()


def verify_api_key(key: str, key_hash: str, secret: str) -> bool:
    """Verify an API key against its stored hash.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        key: The API key to verify.
        key_hash: The stored hash to compare against.
        secret: Server-side secret for HMAC verification.

    Returns:
        True if the key matches the hash, False otherwise.

    Example:
        >>> secret = "my-secret"
        >>> key = 'ldr_test123'
        >>> hashed = hash_api_key(key, secret)
        >>> verify_api_key(key, hashed, secret)
        True
        >>> verify_api_key('ldr_wrong', hashed, secret)
        False
    """
    computed_hash = hash_api_key(key, secret)
    return secrets.compare_digest(computed_hash, key_hash)
