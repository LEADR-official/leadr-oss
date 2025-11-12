"""Tests for device token cryptographic operations."""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from leadr.auth.services.device_token_crypto import (
    generate_access_token,
    generate_refresh_token,
    hash_token,
    validate_access_token,
    validate_refresh_token,
)


class TestGenerateAccessToken:
    """Tests for JWT access token generation."""

    def test_generates_valid_jwt_token(self):
        """Test that generated token is a valid JWT."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token, token_hash = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=secret,
        )

        # Should be a JWT (3 parts separated by dots)
        assert token.count(".") == 2
        assert isinstance(token, str)
        assert len(token) > 50

    def test_token_contains_required_claims(self):
        """Test that JWT contains all required claims."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token, _ = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=secret,
        )

        # Decode without verification to inspect claims
        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded["sub"] == device_id
        assert decoded["game_id"] == str(game_id)
        assert decoded["account_id"] == str(account_id)
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded

    def test_token_expiration_is_correct(self):
        """Test that token expiration is set correctly."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=2)
        secret = "test-secret"

        before = datetime.now(UTC)
        token, _ = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=secret,
        )

        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

        # Expiration should be approximately 2 hours from now
        expected_exp = before + expires_delta
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5

    def test_returns_token_and_hash(self):
        """Test that function returns both token and hash."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        result = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=secret,
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        token, token_hash = result
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert token != token_hash

    def test_hash_is_sha256_hex(self):
        """Test that hash is SHA-256 hexadecimal."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        _, token_hash = generate_access_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            expires_delta=expires_delta,
            secret=secret,
        )

        # SHA-256 hex is 64 characters
        assert len(token_hash) == 64
        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in token_hash)

    def test_each_token_has_unique_jti(self):
        """Test that each token gets a unique JTI."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token1, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)
        token2, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)

        decoded1 = jwt.decode(token1, options={"verify_signature": False})
        decoded2 = jwt.decode(token2, options={"verify_signature": False})

        assert decoded1["jti"] != decoded2["jti"]


class TestValidateAccessToken:
    """Tests for JWT access token validation."""

    def test_validates_correct_token(self):
        """Test that valid token is accepted."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)

        claims = validate_access_token(token, secret)

        assert claims is not None
        assert claims["sub"] == device_id
        assert claims["game_id"] == str(game_id)
        assert claims["account_id"] == str(account_id)

    def test_rejects_expired_token(self):
        """Test that expired token is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(seconds=1)
        secret = "test-secret"

        token, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)

        # Wait for token to expire
        time.sleep(2)

        claims = validate_access_token(token, secret)
        assert claims is None

    def test_rejects_token_with_wrong_secret(self):
        """Test that token signed with different secret is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)

        token, _ = generate_access_token(device_id, game_id, account_id, expires_delta, "secret1")

        claims = validate_access_token(token, "secret2")
        assert claims is None

    def test_rejects_malformed_token(self):
        """Test that malformed token is rejected."""
        claims = validate_access_token("not.a.valid.jwt", "secret")
        assert claims is None

    def test_rejects_tampered_token(self):
        """Test that tampered token is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)

        # Tamper with the token
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.tampered"

        claims = validate_access_token(tampered_token, secret)
        assert claims is None

    def test_returns_all_claims(self):
        """Test that all claims are returned."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        token, _ = generate_access_token(device_id, game_id, account_id, expires_delta, secret)

        claims = validate_access_token(token, secret)

        assert claims is not None
        assert "sub" in claims
        assert "game_id" in claims
        assert "account_id" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert "jti" in claims


class TestHashToken:
    """Tests for token hashing."""

    def test_hashes_token(self):
        """Test that token is hashed."""
        token = "test.jwt.token"
        secret = "test-secret"

        hashed = hash_token(token, secret)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex
        assert hashed != token

    def test_hash_is_deterministic(self):
        """Test that same token produces same hash."""
        token = "test.jwt.token"
        secret = "test-secret"

        hash1 = hash_token(token, secret)
        hash2 = hash_token(token, secret)

        assert hash1 == hash2

    def test_different_tokens_produce_different_hashes(self):
        """Test that different tokens produce different hashes."""
        secret = "test-secret"

        hash1 = hash_token("token1", secret)
        hash2 = hash_token("token2", secret)

        assert hash1 != hash2

    def test_different_secrets_produce_different_hashes(self):
        """Test that same token with different secrets produces different hashes."""
        token = "test.jwt.token"

        hash1 = hash_token(token, "secret1")
        hash2 = hash_token(token, "secret2")

        assert hash1 != hash2

    def test_hash_output_format(self):
        """Test that hash is valid hexadecimal."""
        token = "test.jwt.token"
        secret = "test-secret"

        hashed = hash_token(token, secret)

        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in hashed)


class TestGenerateRefreshToken:
    """Tests for JWT refresh token generation."""

    def test_generates_valid_jwt_token(self):
        """Test that generated refresh token is a valid JWT."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token, token_hash = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=token_version,
            expires_delta=expires_delta,
            secret=secret,
        )

        # Should be a JWT (3 parts separated by dots)
        assert token.count(".") == 2
        assert isinstance(token, str)
        assert len(token) > 50

    def test_token_contains_required_claims_including_version(self):
        """Test that refresh JWT contains all required claims including token_version."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 2
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token, _ = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=token_version,
            expires_delta=expires_delta,
            secret=secret,
        )

        # Decode without verification to inspect claims
        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded["sub"] == device_id
        assert decoded["game_id"] == str(game_id)
        assert decoded["account_id"] == str(account_id)
        assert decoded["token_version"] == token_version
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded

    def test_token_expiration_is_correct(self):
        """Test that refresh token expiration is set correctly."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        before = datetime.now(UTC)
        token, _ = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=token_version,
            expires_delta=expires_delta,
            secret=secret,
        )

        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

        # Expiration should be approximately 30 days from now
        expected_exp = before + expires_delta
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5

    def test_returns_token_and_hash(self):
        """Test that function returns both refresh token and hash."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        result = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=token_version,
            expires_delta=expires_delta,
            secret=secret,
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        token, token_hash = result
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert token != token_hash

    def test_hash_is_sha256_hex(self):
        """Test that refresh token hash is SHA-256 hexadecimal."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        _, token_hash = generate_refresh_token(
            device_id=device_id,
            game_id=game_id,
            account_id=account_id,
            token_version=token_version,
            expires_delta=expires_delta,
            secret=secret,
        )

        # SHA-256 hex is 64 characters
        assert len(token_hash) == 64
        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in token_hash)

    def test_each_token_has_unique_jti(self):
        """Test that each refresh token gets a unique JTI."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token1, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )
        token2, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        decoded1 = jwt.decode(token1, options={"verify_signature": False})
        decoded2 = jwt.decode(token2, options={"verify_signature": False})

        assert decoded1["jti"] != decoded2["jti"]

    def test_different_token_versions_produce_different_tokens(self):
        """Test that different token versions produce different tokens."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token1, _ = generate_refresh_token(
            device_id,
            game_id,
            account_id,
            token_version=1,
            expires_delta=expires_delta,
            secret=secret,
        )
        token2, _ = generate_refresh_token(
            device_id,
            game_id,
            account_id,
            token_version=2,
            expires_delta=expires_delta,
            secret=secret,
        )

        decoded1 = jwt.decode(token1, options={"verify_signature": False})
        decoded2 = jwt.decode(token2, options={"verify_signature": False})

        assert decoded1["token_version"] == 1
        assert decoded2["token_version"] == 2
        assert token1 != token2


class TestValidateRefreshToken:
    """Tests for JWT refresh token validation."""

    def test_validates_correct_token(self):
        """Test that valid refresh token is accepted."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        claims = validate_refresh_token(token, secret)

        assert claims is not None
        assert claims["sub"] == device_id
        assert claims["game_id"] == str(game_id)
        assert claims["account_id"] == str(account_id)
        assert claims["token_version"] == token_version

    def test_rejects_expired_token(self):
        """Test that expired refresh token is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(seconds=1)
        secret = "test-secret"

        token, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        # Wait for token to expire
        time.sleep(2)

        claims = validate_refresh_token(token, secret)
        assert claims is None

    def test_rejects_token_with_wrong_secret(self):
        """Test that refresh token signed with different secret is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)

        token, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, "secret1"
        )

        claims = validate_refresh_token(token, "secret2")
        assert claims is None

    def test_rejects_malformed_token(self):
        """Test that malformed refresh token is rejected."""
        claims = validate_refresh_token("not.a.valid.jwt", "secret")
        assert claims is None

    def test_rejects_tampered_token(self):
        """Test that tampered refresh token is rejected."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 1
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        # Tamper with the token
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.tampered"

        claims = validate_refresh_token(tampered_token, secret)
        assert claims is None

    def test_returns_all_claims_including_version(self):
        """Test that all claims including token_version are returned."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 3
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        token, _ = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        claims = validate_refresh_token(token, secret)

        assert claims is not None
        assert "sub" in claims
        assert "game_id" in claims
        assert "account_id" in claims
        assert "token_version" in claims
        assert claims["token_version"] == 3
        assert "exp" in claims
        assert "iat" in claims
        assert "jti" in claims


class TestTokenGenerationAndValidation:
    """Integration tests for token generation and validation."""

    def test_full_cycle_with_generated_token(self):
        """Test complete token lifecycle."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        expires_delta = timedelta(hours=1)
        secret = "test-secret"

        # Generate token
        token, token_hash = generate_access_token(
            device_id, game_id, account_id, expires_delta, secret
        )

        # Validate token
        claims = validate_access_token(token, secret)
        assert claims is not None
        assert claims["sub"] == device_id
        assert claims["game_id"] == str(game_id)
        assert claims["account_id"] == str(account_id)

        # Hash matches
        rehashed = hash_token(token, secret)
        assert rehashed == token_hash

    def test_multiple_tokens_can_be_validated_independently(self):
        """Test that multiple tokens work independently."""
        secret = "test-secret"
        expires_delta = timedelta(hours=1)

        # Generate tokens for different devices
        token1, _ = generate_access_token(str(uuid4()), uuid4(), uuid4(), expires_delta, secret)
        token2, _ = generate_access_token(str(uuid4()), uuid4(), uuid4(), expires_delta, secret)

        # Both should validate
        claims1 = validate_access_token(token1, secret)
        claims2 = validate_access_token(token2, secret)

        assert claims1 is not None
        assert claims2 is not None
        assert claims1["sub"] != claims2["sub"]

    def test_full_cycle_with_refresh_token(self):
        """Test complete refresh token lifecycle."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        token_version = 2
        expires_delta = timedelta(days=30)
        secret = "test-secret"

        # Generate refresh token
        token, token_hash = generate_refresh_token(
            device_id, game_id, account_id, token_version, expires_delta, secret
        )

        # Validate refresh token
        claims = validate_refresh_token(token, secret)
        assert claims is not None
        assert claims["sub"] == device_id
        assert claims["game_id"] == str(game_id)
        assert claims["account_id"] == str(account_id)
        assert claims["token_version"] == token_version

        # Hash matches
        rehashed = hash_token(token, secret)
        assert rehashed == token_hash

    def test_access_and_refresh_tokens_are_independent(self):
        """Test that access and refresh tokens can coexist."""
        device_id = str(uuid4())
        game_id = uuid4()
        account_id = uuid4()
        secret = "test-secret"

        # Generate both token types
        access_token, access_hash = generate_access_token(
            device_id, game_id, account_id, timedelta(hours=1), secret
        )
        refresh_token, refresh_hash = generate_refresh_token(
            device_id, game_id, account_id, 1, timedelta(days=30), secret
        )

        # Both should validate independently
        access_claims = validate_access_token(access_token, secret)
        refresh_claims = validate_refresh_token(refresh_token, secret)

        assert access_claims is not None
        assert refresh_claims is not None
        assert access_token != refresh_token
        assert access_hash != refresh_hash
