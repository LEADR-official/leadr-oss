import os
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    APP: str = "LEADR"
    ENV: str = Field(default=...)
    DEBUG: bool = False

    # API Configuration
    API_PREFIX: str = "/v1"

    BASE_URL: HttpUrl = HttpUrl("http://localhost:8000")
    DASHBOARD_URL: HttpUrl = HttpUrl("http://localhost:8000")

    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "leadr"
    DB_USER: str = "leadr"
    DB_PASSWORD: str = "leadr"

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 20
    DB_POOL_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DB_ECHO: bool = False  # Set to True to log SQL queries (dev/debug)

    # JWT Configuration
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_LIFETIME_SECONDS: int = 3600

    # Crypto/Keys Configuration
    KEYS_PATH: Path = PROJ_ROOT / ".keys"

    SOURCE_OAUTH_BASE_URL: HttpUrl = HttpUrl("http://localhost:8000")

    ENABLE_ADMIN_API: bool = True
    ENABLE_CLIENT_API: bool = True

    TESTING_EMAIL: str = "hello@example.com"

    MAILGUN_API_KEY: str = "mailgun_api_key"
    MAILGUN_DOMAIN: str = "example.mailgun.org"


class Settings(CommonSettings):
    pass


class TestSettings(CommonSettings):
    pass


settings = (
    TestSettings(_env_file=Path(PROJ_ROOT, ".env.test"))  # type: ignore[reportCallIssue]
    if os.environ.get("ENV") == "TEST"
    else Settings(_env_file=Path(PROJ_ROOT, ".env"))  # type: ignore[reportCallIssue]
)
