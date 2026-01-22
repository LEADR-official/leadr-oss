"""Tests for application configuration."""

from unittest.mock import patch


class TestFromEmailConfig:
    """Test FROM_EMAIL configuration and default_from_email property."""

    def test_from_email_defaults_to_noreply(self):
        """Test that FROM_EMAIL defaults to 'noreply' when not set."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            from leadr.config import CommonSettings

            # Create settings without FROM_EMAIL set
            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="test.mailgun.org",
            )
            assert settings.FROM_EMAIL == "noreply"

    def test_custom_from_email_value(self):
        """Test that custom FROM_EMAIL value is used."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            from leadr.config import CommonSettings

            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="test.mailgun.org",
                FROM_EMAIL="support",
            )
            assert settings.FROM_EMAIL == "support"

    def test_default_from_email_property_combines_from_email_and_domain(self):
        """Test that default_from_email returns {FROM_EMAIL}@{MAILGUN_DOMAIN}."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            from leadr.config import CommonSettings

            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="test.mailgun.org",
                FROM_EMAIL="noreply",
            )
            assert settings.default_from_email == "noreply@test.mailgun.org"

    def test_default_from_email_with_custom_from_email(self):
        """Test default_from_email with custom FROM_EMAIL."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            from leadr.config import CommonSettings

            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="mail.leadr.gg",
                FROM_EMAIL="hello",
            )
            assert settings.default_from_email == "hello@mail.leadr.gg"

    def test_default_from_email_with_different_mailgun_domain(self):
        """Test default_from_email uses MAILGUN_DOMAIN correctly."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            from leadr.config import CommonSettings

            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="notifications.example.com",
            )
            assert settings.default_from_email == "noreply@notifications.example.com"
