"""Tests for application configuration."""

from unittest.mock import patch

import pytest

from leadr.config import CommonSettings


class TestFromEmailConfig:
    """Test FROM_EMAIL configuration and default_from_email property."""

    def test_from_email_defaults_to_noreply(self):
        """Test that FROM_EMAIL defaults to 'noreply' when not set."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
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
            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
                MAILGUN_DOMAIN="notifications.example.com",
            )
            assert settings.default_from_email == "noreply@notifications.example.com"


class TestJobModeConfig:
    """Test JOB_MODE configuration for standalone job scripts."""

    def test_job_mode_bypasses_api_validation(self):
        """Test that JOB_MODE=True allows neither API to be enabled."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            # Should NOT raise even though both APIs are disabled
            settings = CommonSettings(
                ENV="TEST",
                JOB_MODE=True,
                ENABLE_ADMIN_API=False,
                ENABLE_CLIENT_API=False,
                SUPERADMIN_API_KEY="ldr_test_key",
            )
            assert settings.JOB_MODE is True
            assert settings.ENABLE_ADMIN_API is False
            assert settings.ENABLE_CLIENT_API is False

    def test_job_mode_defaults_to_false(self):
        """Test that JOB_MODE defaults to False."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            settings = CommonSettings(
                ENV="TEST",
                ENABLE_ADMIN_API=True,
                SUPERADMIN_API_KEY="ldr_test_key",
            )
            assert settings.JOB_MODE is False

    def test_api_validation_fails_without_job_mode(self):
        """Test that validation fails when neither API is enabled and JOB_MODE is False."""
        with patch.dict("os.environ", {"ENV": "TEST"}, clear=False):
            with pytest.raises(ValueError) as exc_info:
                CommonSettings(
                    ENV="TEST",
                    JOB_MODE=False,
                    ENABLE_ADMIN_API=False,
                    ENABLE_CLIENT_API=False,
                    SUPERADMIN_API_KEY="ldr_test_key",
                )
            assert "ENABLE_ADMIN_API or ENABLE_CLIENT_API" in str(exc_info.value)
