"""Application configuration management.

This module defines the configuration settings for the LEADR application using
Pydantic Settings. Configuration values are loaded from environment variables
and .env files, with validation and type checking.

Environment files:
    - .env: Production/development configuration (default)
    - .env.test: Test environment configuration (when ENV=TEST)

Example:
    Settings are automatically loaded based on the ENV variable:

    >>> from leadr.config import settings
    >>> settings.API_PREFIX
    '/v1'
"""

import os
from pathlib import Path

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


class CommonSettings(BaseSettings):
    """Base configuration settings shared across all environments.

    This class defines all configuration fields that are common to both
    production and test environments. Specific environment classes can
    override defaults or add environment-specific settings.

    All settings can be configured via environment variables matching the
    field names (case-sensitive).
    """

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    APP: str = Field(
        default="LEADR",
        description="Application name identifier",
    )
    ENV: str = Field(
        default=...,
        description="Environment name (e.g., 'DEV', 'PROD', 'TEST'). Required.",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging and error details",
    )

    # API Configuration
    API_PREFIX: str = Field(
        default="/v1",
        description="API route prefix for versioning (e.g., '/v1')",
    )

    BASE_URL: HttpUrl = Field(
        default=HttpUrl("http://localhost:8000"),
        description="Base URL for the API server (e.g., 'https://api.leadr.gg')",
    )
    DASHBOARD_URL: HttpUrl = Field(
        default=HttpUrl("http://localhost:8000"),
        description="URL for the web dashboard (e.g., 'https://dashboard.leadr.gg')",
    )

    # Database Configuration
    DB_HOST: str = Field(
        default="localhost",
        description="PostgreSQL database host",
    )
    DB_PORT: int = Field(
        default=5432,
        description="PostgreSQL database port",
    )
    DB_NAME: str = Field(
        default="leadr",
        description="PostgreSQL database name",
    )
    DB_USER: str = Field(
        default="leadr",
        description="PostgreSQL database user",
    )
    DB_PASSWORD: str = Field(
        default="leadr",
        description="PostgreSQL database password",
    )

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(
        default=20,
        description="Number of database connections to maintain in the pool",
    )
    DB_POOL_MAX_OVERFLOW: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool size",
    )
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        description="Recycle database connections after this many seconds (default: 1 hour)",
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Log all SQL queries to stdout (useful for debugging)",
    )

    # JWT Configuration
    JWT_SECRET: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="Secret key for JWT token signing. MUST be changed in production.",
    )
    JWT_LIFETIME_SECONDS: int = Field(
        default=3600,
        description="JWT token lifetime in seconds (default: 1 hour)",
    )

    # Device Token Configuration (Phase 1: Short-lived tokens + refresh)
    ACCESS_TOKEN_EXPIRY_HOURS: int = Field(
        default=24,
        description="Device access token expiration time in hours (default: 24 hours)",
    )
    REFRESH_TOKEN_EXPIRY_DAYS: int = Field(
        default=30,
        description="Device refresh token expiration time in days (default: 30 days)",
    )

    # API Key Configuration
    API_KEY_SECRET: str = Field(
        default="your-super-secret-api-key-pepper-change-in-production",
        description="Secret pepper for API key hashing. MUST be changed in production.",
    )

    # Crypto/Keys Configuration
    KEYS_PATH: Path = Field(
        default=PROJ_ROOT / ".keys",
        description="Directory path for storing cryptographic keys",
    )

    SOURCE_OAUTH_BASE_URL: HttpUrl = Field(
        default=HttpUrl("http://localhost:8000"),
        description="Base URL for OAuth provider",
    )

    ENABLE_ADMIN_API: bool = Field(
        default=False,
        description="Enable admin API endpoints",
    )
    ENABLE_CLIENT_API: bool = Field(
        default=False,
        description="Enable client API endpoints",
    )

    TESTING_EMAIL: str = Field(
        default="hello@example.com",
        description="Email address used for testing purposes",
    )

    MAILGUN_API_KEY: str = Field(
        default="mailgun_api_key",
        description="Mailgun API key for email sending",
    )
    MAILGUN_DOMAIN: str = Field(
        default="example.mailgun.org",
        description="Mailgun domain for email sending",
    )

    # Background Task Configuration
    BACKGROUND_TASK_TEMPLATE_INTERVAL: int = Field(
        default=60,
        description="Interval in seconds for processing due board templates (default: 60s)",
    )
    BACKGROUND_TASK_EXPIRE_INTERVAL: int = Field(
        default=60,
        description="Interval in seconds for expiring boards (default: 60s)",
    )

    # Anti-Cheat Configuration
    ANTICHEAT_ENABLED: bool = Field(
        default=False,
        description="Enable anti-cheat checks on score submissions",
    )
    ANTICHEAT_LOGGING_ONLY: bool = Field(
        default=True,
        description="Log anti-cheat detections but don't reject/flag submissions (dry-run mode)",
    )

    # Rate Limit Tiers (submissions per hour)
    ANTICHEAT_RATE_LIMIT_TIER_A: int = Field(
        default=100,
        description="Rate limit for Tier A (trusted) devices: submissions per hour",
    )
    ANTICHEAT_RATE_LIMIT_TIER_B: int = Field(
        default=50,
        description="Rate limit for Tier B (verified) devices: submissions per hour",
    )
    ANTICHEAT_RATE_LIMIT_TIER_C: int = Field(
        default=20,
        description="Rate limit for Tier C (unverified) devices: submissions per hour",
    )

    # Outlier Detection Thresholds (standard deviations)
    ANTICHEAT_OUTLIER_THRESHOLD_TIER_A: float = Field(
        default=4.0,
        description="Outlier threshold for Tier A devices: standard deviations from mean",
    )
    ANTICHEAT_OUTLIER_THRESHOLD_TIER_B: float = Field(
        default=3.0,
        description="Outlier threshold for Tier B devices: standard deviations from mean",
    )
    ANTICHEAT_OUTLIER_THRESHOLD_TIER_C: float = Field(
        default=2.5,
        description="Outlier threshold for Tier C devices: standard deviations from mean",
    )

    # Other Anti-Cheat Thresholds
    ANTICHEAT_MIN_SAMPLES_FOR_STATS: int = Field(
        default=10,
        description=(
            "Minimum number of scores required before statistical outlier detection is enabled"
        ),
    )
    ANTICHEAT_DUPLICATE_WINDOW_SECONDS: int = Field(
        default=300,
        description=(
            "Time window in seconds for detecting duplicate score submissions (default: 5 minutes)"
        ),
    )
    ANTICHEAT_VELOCITY_THRESHOLD_SECONDS: float = Field(
        default=2.0,
        description="Minimum time between submissions to avoid velocity detection (in seconds)",
    )

    @model_validator(mode="after")
    def validate_api_enabled(self):
        """Ensure at least one API (Admin or Client) is enabled."""
        if not self.ENABLE_ADMIN_API and not self.ENABLE_CLIENT_API:
            raise ValueError("At least one of ENABLE_ADMIN_API or ENABLE_CLIENT_API must be True")
        return self


class Settings(CommonSettings):
    """Production/development environment settings.

    Inherits all settings from CommonSettings. Loads configuration from
    the .env file at the project root.

    This is the default settings class used when ENV != 'TEST'.
    """


class TestSettings(CommonSettings):
    """Test environment settings.

    Inherits all settings from CommonSettings. Loads configuration from
    the .env.test file at the project root.

    Used automatically when ENV='TEST' (set by test.sh script).
    Test-specific overrides can be added here.
    """


settings = (
    TestSettings(_env_file=Path(PROJ_ROOT, ".env.test"))  # type: ignore[reportCallIssue]
    if os.environ.get("ENV") == "TEST"
    else Settings(_env_file=Path(PROJ_ROOT, ".env"))  # type: ignore[reportCallIssue]
)
