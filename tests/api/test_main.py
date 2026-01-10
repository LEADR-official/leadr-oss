"""Tests for main.py application factory and lifespan."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from api.main import _get_api_title, create_app, lifespan


class TestGetApiTitle:
    """Tests for _get_api_title function."""

    @patch("api.main.settings")
    def test_returns_admin_and_client_title_when_both_enabled(self, mock_settings) -> None:
        """Test title when both Admin and Client APIs are enabled."""
        mock_settings.ENABLE_ADMIN_API = True
        mock_settings.ENABLE_CLIENT_API = True

        title = _get_api_title()
        assert "Admin & Client API" in title

    @patch("api.main.settings")
    def test_returns_admin_only_title(self, mock_settings) -> None:
        """Test title when only Admin API is enabled."""
        mock_settings.ENABLE_ADMIN_API = True
        mock_settings.ENABLE_CLIENT_API = False

        title = _get_api_title()
        assert "Admin API" in title
        assert "Client" not in title

    @patch("api.main.settings")
    def test_returns_client_only_title(self, mock_settings) -> None:
        """Test title when only Client API is enabled."""
        mock_settings.ENABLE_ADMIN_API = False
        mock_settings.ENABLE_CLIENT_API = True

        title = _get_api_title()
        assert "Client API" in title
        assert "Admin" not in title

    @patch("api.main.settings")
    def test_raises_when_neither_enabled(self, mock_settings) -> None:
        """Test that RuntimeError is raised when no APIs are enabled."""
        mock_settings.ENABLE_ADMIN_API = False
        mock_settings.ENABLE_CLIENT_API = False

        with pytest.raises(RuntimeError, match="ENABLE_ADMIN_API or ENABLE_CLIENT_API"):
            _get_api_title()


class TestCreateApp:
    """Tests for create_app factory function."""

    @patch("api.main.settings")
    def test_create_app_with_custom_title(self, mock_settings) -> None:
        """Test creating app with custom title."""
        mock_settings.ENABLE_ADMIN_API = True
        mock_settings.ENABLE_CLIENT_API = True
        mock_settings.API_PREFIX = "/v1"
        mock_settings.DEV_OVERRIDE_IP = None

        app = create_app(title="Custom Title", lifespan_override=None)
        assert app.title == "Custom Title"

    @patch("api.main.settings")
    def test_create_app_with_custom_description(self, mock_settings) -> None:
        """Test creating app with custom description."""
        mock_settings.ENABLE_ADMIN_API = True
        mock_settings.ENABLE_CLIENT_API = True
        mock_settings.API_PREFIX = "/v1"
        mock_settings.DEV_OVERRIDE_IP = None

        app = create_app(description="Custom Description", lifespan_override=None)
        assert app.description == "Custom Description"

    @patch("api.main.settings")
    def test_create_app_with_custom_version(self, mock_settings) -> None:
        """Test creating app with custom version."""
        mock_settings.ENABLE_ADMIN_API = True
        mock_settings.ENABLE_CLIENT_API = True
        mock_settings.API_PREFIX = "/v1"
        mock_settings.DEV_OVERRIDE_IP = None

        app = create_app(version="2.0.0", lifespan_override=None)
        assert app.version == "2.0.0"


class TestLifespan:
    """Tests for lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_production_initializes_geoip(self) -> None:
        """Test that GeoIP service is initialized in non-TEST environment."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_geoip_service = AsyncMock()
        mock_geoip_service.initialize = AsyncMock()
        mock_geoip_service.close = MagicMock()

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()
        mock_scheduler.add_task = MagicMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("api.main.settings") as mock_settings,
            patch("api.main.GeoIPService", return_value=mock_geoip_service),
            patch("api.main.async_session_factory", mock_session_factory),
            patch("api.main.ensure_superadmin_exists", AsyncMock()),
            patch("api.main.get_scheduler", return_value=mock_scheduler),
            patch("api.main.engine", mock_engine),
        ):
            mock_settings.ENV = "PROD"
            mock_settings.MAXMIND_ACCOUNT_ID = "123"
            mock_settings.MAXMIND_LICENSE_KEY = "key"
            mock_settings.MAXMIND_CITY_DB_URL = "http://city.db"
            mock_settings.MAXMIND_COUNTRY_DB_URL = "http://country.db"
            mock_settings.GEOIP_DATABASE_PATH = ".geoip"
            mock_settings.GEOIP_REFRESH_DAYS = 7
            mock_settings.ENABLE_ADMIN_API = True
            mock_settings.BACKGROUND_TASK_TEMPLATE_INTERVAL = 60
            mock_settings.BACKGROUND_TASK_EXPIRE_INTERVAL = 60
            mock_settings.BACKGROUND_TASK_NONCE_CLEANUP_INTERVAL = 60

            async with lifespan(mock_app):
                # Verify GeoIP was initialized
                mock_geoip_service.initialize.assert_called_once()
                assert mock_app.state.geoip_service == mock_geoip_service

            # Verify cleanup happened
            mock_geoip_service.close.assert_called_once()
            mock_scheduler.stop.assert_called_once()
            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_registers_background_tasks_when_admin_enabled(self) -> None:
        """Test that background tasks are registered when ENABLE_ADMIN_API is True."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()
        mock_scheduler.add_task = MagicMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("api.main.settings") as mock_settings,
            patch("api.main.async_session_factory", mock_session_factory),
            patch("api.main.ensure_superadmin_exists", AsyncMock()),
            patch("api.main.get_scheduler", return_value=mock_scheduler),
            patch("api.main.engine", mock_engine),
        ):
            mock_settings.ENV = "TEST"
            mock_settings.ENABLE_ADMIN_API = True
            mock_settings.BACKGROUND_TASK_TEMPLATE_INTERVAL = 60
            mock_settings.BACKGROUND_TASK_EXPIRE_INTERVAL = 60
            mock_settings.BACKGROUND_TASK_NONCE_CLEANUP_INTERVAL = 60

            async with lifespan(mock_app):
                # Verify background tasks were registered
                assert mock_scheduler.add_task.call_count == 3
                task_names = [call[0][0] for call in mock_scheduler.add_task.call_args_list]
                assert "process-due-templates" in task_names
                assert "expire-boards" in task_names
                assert "cleanup-expired-nonces" in task_names

    @pytest.mark.asyncio
    async def test_lifespan_skips_background_tasks_when_admin_disabled(self) -> None:
        """Test that background tasks are NOT registered when ENABLE_ADMIN_API is False."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()
        mock_scheduler.add_task = MagicMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("api.main.settings") as mock_settings,
            patch("api.main.async_session_factory", mock_session_factory),
            patch("api.main.ensure_superadmin_exists", AsyncMock()),
            patch("api.main.get_scheduler", return_value=mock_scheduler),
            patch("api.main.engine", mock_engine),
        ):
            mock_settings.ENV = "TEST"
            mock_settings.ENABLE_ADMIN_API = False

            async with lifespan(mock_app):
                # Verify no background tasks were registered
                assert mock_scheduler.add_task.call_count == 0

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_handles_none_geoip_service(self) -> None:
        """Test that shutdown handles None geoip_service gracefully."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_app.state.geoip_service = None

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()
        mock_scheduler.add_task = MagicMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("api.main.settings") as mock_settings,
            patch("api.main.async_session_factory", mock_session_factory),
            patch("api.main.ensure_superadmin_exists", AsyncMock()),
            patch("api.main.get_scheduler", return_value=mock_scheduler),
            patch("api.main.engine", mock_engine),
        ):
            mock_settings.ENV = "TEST"
            mock_settings.ENABLE_ADMIN_API = False

            # Should not raise even with geoip_service = None
            async with lifespan(mock_app):
                pass

            # Engine should still be disposed
            mock_engine.dispose.assert_called_once()
