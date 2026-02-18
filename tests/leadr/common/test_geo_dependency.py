"""Tests for GeoInfo FastAPI dependency."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from leadr.common.dependencies import get_geo_info
from leadr.common.geoip import GeoInfo


class TestGetGeoInfoDependency:
    """Tests for get_geo_info FastAPI dependency."""

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_returns_geo_info_when_lookup_succeeds(self, mock_settings):
        """Test that dependency returns GeoInfo when geo lookup succeeds."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/New_York",
            country="US",
            city="New York",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"
        assert data["country"] == "US"
        assert data["city"] == "New York"
        mock_geoip_service.get_geo_info.assert_called_once_with("8.8.8.8")

    @pytest.mark.asyncio
    async def test_returns_empty_geo_info_when_service_not_available(self):
        """Test that dependency returns empty GeoInfo when geoip_service is None."""
        app = FastAPI()

        # No geoip_service on app.state
        app.state.geoip_service = None

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.extract_client_ip", return_value=None)
    @patch("leadr.common.dependencies.settings")
    async def test_returns_empty_geo_info_when_no_client_ip(self, mock_settings, mock_extract_ip):
        """Test that dependency returns empty GeoInfo when client IP cannot be extracted."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        mock_geoip_service = Mock()
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None
        # geo lookup should not be called when there's no IP
        mock_geoip_service.get_geo_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_geo_info_when_lookup_returns_none(self):
        """Test that dependency returns empty GeoInfo when geo lookup returns None."""
        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = None
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "192.168.1.1"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None

    @pytest.mark.asyncio
    async def test_returns_empty_geo_info_when_service_raises_exception(self):
        """Test that dependency returns empty GeoInfo when geo service raises exception."""
        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.side_effect = Exception("Database error")
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        # Should succeed even though geo lookup failed
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_uses_dev_override_ip_when_set(self, mock_settings):
        """Test that dependency uses DEV_OVERRIDE_IP when configured."""
        mock_settings.DEV_OVERRIDE_IP = "8.8.4.4"

        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/Los_Angeles",
            country="US",
            city="Los Angeles",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/Los_Angeles"
        # Should use dev override IP, not X-Real-IP
        mock_geoip_service.get_geo_info.assert_called_once_with("8.8.4.4")

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_extracts_ip_from_x_real_ip_header(self, mock_settings):
        """Test that dependency extracts IP from X-Real-IP header."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="Europe/London",
            country="GB",
            city="London",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse({"timezone": geo.timezone})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        assert response.status_code == 200
        mock_geoip_service.get_geo_info.assert_called_once_with("8.8.8.8")

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_extracts_ip_from_x_forwarded_for_header(self, mock_settings):
        """Test that dependency extracts leftmost IP from X-Forwarded-For header."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="Europe/London",
            country="GB",
            city="London",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse({"timezone": geo.timezone})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/test", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
            )

        assert response.status_code == 200
        # Should use leftmost IP (original client)
        mock_geoip_service.get_geo_info.assert_called_once_with("1.2.3.4")

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_extracts_ip_from_cf_connecting_ip_header(self, mock_settings):
        """Test that dependency extracts IP from CF-Connecting-IP header."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="Asia/Tokyo",
            country="JP",
            city="Tokyo",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse({"timezone": geo.timezone})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"CF-Connecting-IP": "1.1.1.1"})

        assert response.status_code == 200
        mock_geoip_service.get_geo_info.assert_called_once_with("1.1.1.1")

    @pytest.mark.asyncio
    @patch("leadr.common.dependencies.settings")
    async def test_header_priority_order(self, mock_settings):
        """Test that dependency checks headers in correct priority order."""
        mock_settings.DEV_OVERRIDE_IP = None

        app = FastAPI()

        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/New_York",
            country="US",
            city="New York",
        )
        app.state.geoip_service = mock_geoip_service

        @app.get("/test")
        async def test_route(request: Request):
            _ = await get_geo_info(request)
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/test",
                headers={
                    "X-Real-IP": "1.1.1.1",
                    "X-Forwarded-For": "2.2.2.2",
                    "CF-Connecting-IP": "3.3.3.3",
                },
            )

        assert response.status_code == 200
        # Should use X-Real-IP (highest priority)
        mock_geoip_service.get_geo_info.assert_called_once_with("1.1.1.1")

    @pytest.mark.asyncio
    async def test_returns_empty_geo_info_when_app_state_missing(self):
        """Test that dependency handles missing geoip_service attribute gracefully."""
        app = FastAPI()

        # Don't set geoip_service at all on app.state

        @app.get("/test")
        async def test_route(request: Request):
            geo = await get_geo_info(request)
            return JSONResponse(
                {
                    "timezone": geo.timezone,
                    "country": geo.country,
                    "city": geo.city,
                }
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None
