"""Tests for API key generation and cryptographic operations."""

import re

from leadr.auth.services.api_key_crypto import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
)
from leadr.config import settings


class TestGenerateAPIKey:
    """Test suite for API key generation."""

    def test_generates_key_with_ldr_prefix(self):
        """Test that generated keys start with 'ldr_' prefix."""
        key = generate_api_key()
        assert key.startswith("ldr_")

    def test_generates_key_with_sufficient_entropy(self):
        """Test that generated keys have sufficient length for security."""
        key = generate_api_key()
        # Remove prefix and check remaining length
        key_without_prefix = key[4:]
        # Should be at least 32 characters (representing ~24 bytes)
        assert len(key_without_prefix) >= 32

    def test_generates_unique_keys(self):
        """Test that each call generates a unique key."""
        keys = [generate_api_key() for _ in range(100)]
        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_generates_url_safe_characters(self):
        """Test that generated keys only contain URL-safe characters."""
        key = generate_api_key()
        key_without_prefix = key[4:]
        # Should only contain alphanumeric, hyphen, and underscore (URL-safe base64)
        assert re.match(r"^[A-Za-z0-9_-]+$", key_without_prefix)

    def test_key_format_is_consistent(self):
        """Test that all generated keys follow the same format."""
        keys = [generate_api_key() for _ in range(10)]
        for key in keys:
            assert key.startswith("ldr_")
            assert len(key) > 36  # ldr_ + at least 32 chars


class TestHashAPIKey:
    """Test suite for API key hashing."""

    def test_hashes_api_key(self):
        """Test that API keys can be hashed with secret."""
        key = "ldr_test123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != key  # Hash should not equal original

    def test_hash_is_deterministic(self):
        """Test that hashing the same key with same secret produces the same hash."""
        key = "ldr_test123456789012345678901234"
        hash1 = hash_api_key(key, settings.API_KEY_SECRET)
        hash2 = hash_api_key(key, settings.API_KEY_SECRET)

        assert hash1 == hash2

    def test_different_keys_produce_different_hashes(self):
        """Test that different keys produce different hashes."""
        key1 = "ldr_test123456789012345678901234"
        key2 = "ldr_test987654321098765432109876"

        hash1 = hash_api_key(key1, settings.API_KEY_SECRET)
        hash2 = hash_api_key(key2, settings.API_KEY_SECRET)

        assert hash1 != hash2

    def test_different_secrets_produce_different_hashes(self):
        """Test that same key with different secrets produces different hashes."""
        key = "ldr_test123456789012345678901234"
        secret1 = "secret1"
        secret2 = "secret2"

        hash1 = hash_api_key(key, secret1)
        hash2 = hash_api_key(key, secret2)

        assert hash1 != hash2

    def test_hash_output_format(self):
        """Test that hash output is in expected format."""
        key = "ldr_test123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        # Should be a hex string (HMAC-SHA256 produces 64 hex chars)
        assert len(hashed) == 64
        assert re.match(r"^[a-f0-9]{64}$", hashed)


class TestVerifyAPIKey:
    """Test suite for API key verification."""

    def test_verifies_correct_key(self):
        """Test that correct key verification returns True with correct secret."""
        key = "ldr_test123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        assert verify_api_key(key, hashed, settings.API_KEY_SECRET) is True

    def test_rejects_incorrect_key(self):
        """Test that incorrect key verification returns False."""
        correct_key = "ldr_test123456789012345678901234"
        wrong_key = "ldr_wrong123456789012345678901234"
        hashed = hash_api_key(correct_key, settings.API_KEY_SECRET)

        assert verify_api_key(wrong_key, hashed, settings.API_KEY_SECRET) is False

    def test_rejects_key_without_prefix(self):
        """Test that keys without ldr_ prefix are rejected."""
        key = "ldr_test123456789012345678901234"
        key_without_prefix = "test123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        assert verify_api_key(key_without_prefix, hashed, settings.API_KEY_SECRET) is False

    def test_rejects_modified_hash(self):
        """Test that modified hashes cause verification to fail."""
        key = "ldr_test123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)
        modified_hash = hashed[:-1] + "0"  # Change last character

        assert verify_api_key(key, modified_hash, settings.API_KEY_SECRET) is False

    def test_rejects_wrong_secret(self):
        """Test that verification fails with wrong secret."""
        key = "ldr_test123456789012345678901234"
        correct_secret = "correct-secret"
        wrong_secret = "wrong-secret"
        hashed = hash_api_key(key, correct_secret)

        assert verify_api_key(key, hashed, wrong_secret) is False

    def test_case_sensitivity(self):
        """Test that verification is case-sensitive."""
        key = "ldr_test123456789012345678901234"
        key_different_case = "ldr_TEST123456789012345678901234"
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        assert verify_api_key(key_different_case, hashed, settings.API_KEY_SECRET) is False


class TestAPIKeyGenerationAndVerification:
    """Integration tests for the full generate-hash-verify cycle."""

    def test_full_cycle_with_generated_key(self):
        """Test that a generated key can be hashed and verified with secret."""
        key = generate_api_key()
        hashed = hash_api_key(key, settings.API_KEY_SECRET)

        assert verify_api_key(key, hashed, settings.API_KEY_SECRET) is True

    def test_multiple_keys_can_be_verified_independently(self):
        """Test that multiple keys can be generated and verified correctly."""
        keys_and_hashes = [(generate_api_key(), None) for _ in range(5)]
        keys_and_hashes = [
            (key, hash_api_key(key, settings.API_KEY_SECRET)) for key, _ in keys_and_hashes
        ]

        # Each key should verify against its own hash
        for key, hashed in keys_and_hashes:
            assert verify_api_key(key, hashed, settings.API_KEY_SECRET) is True

        # Keys should not verify against other hashes
        for i, (key, _) in enumerate(keys_and_hashes):
            for j, (_, other_hash) in enumerate(keys_and_hashes):
                if i != j:
                    assert verify_api_key(key, other_hash, settings.API_KEY_SECRET) is False
