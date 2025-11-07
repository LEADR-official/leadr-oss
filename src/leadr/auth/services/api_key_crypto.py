"""Cryptographic operations for API keys."""

import hashlib
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


def hash_api_key(key: str) -> str:
    """Hash an API key for secure storage.

    Uses SHA-256 to create a one-way hash of the API key.
    The hash is deterministic, allowing verification, but the
    original key cannot be recovered from the hash.

    Args:
        key: The API key to hash.

    Returns:
        A hexadecimal string representation of the SHA-256 hash.

    Example:
        >>> hash1 = hash_api_key('ldr_test123')
        >>> hash2 = hash_api_key('ldr_test123')
        >>> hash1 == hash2
        True
        >>> len(hash1)
        64
    """
    key_bytes = key.encode("utf-8")
    hash_obj = hashlib.sha256(key_bytes)
    return hash_obj.hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its stored hash.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        key: The API key to verify.
        key_hash: The stored hash to compare against.

    Returns:
        True if the key matches the hash, False otherwise.

    Example:
        >>> key = 'ldr_test123'
        >>> hashed = hash_api_key(key)
        >>> verify_api_key(key, hashed)
        True
        >>> verify_api_key('ldr_wrong', hashed)
        False
    """
    computed_hash = hash_api_key(key)
    return secrets.compare_digest(computed_hash, key_hash)
