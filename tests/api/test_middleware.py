"""Tests for API middleware."""

import asyncio
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from leadr.common.geoip import GeoInfo


class TestGeoIPMiddleware:
    """Tests for GeoIP middleware."""

    @pytest.mark.asyncio
    async def test_extracts_ip_from_x_real_ip_header(self):
        """Test that middleware extracts IP from X-Real-IP header."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse(
                {
                    "timezone": getattr(request.state, "geo_timezone", None),
                    "country": getattr(request.state, "geo_country", None),
                    "city": getattr(request.state, "geo_city", None),
                }
            )

        # Test with X-Real-IP header
        from httpx import ASGITransport, AsyncClient

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
    async def test_extracts_ip_from_x_forwarded_for_header(self):
        """Test that middleware extracts leftmost IP from X-Forwarded-For header."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="Europe/London",
            country="GB",
            city="London",
        )

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse(
                {
                    "timezone": getattr(request.state, "geo_timezone", None),
                    "country": getattr(request.state, "geo_country", None),
                    "city": getattr(request.state, "geo_city", None),
                }
            )

        # Test with X-Forwarded-For header (proxy chain)
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/test", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "Europe/London"
        assert data["country"] == "GB"
        assert data["city"] == "London"
        # Should use leftmost IP (original client)
        mock_geoip_service.get_geo_info.assert_called_once_with("1.2.3.4")

    @pytest.mark.asyncio
    async def test_extracts_ip_from_cf_connecting_ip_header(self):
        """Test that middleware extracts IP from CF-Connecting-IP header."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="Asia/Tokyo",
            country="JP",
            city="Tokyo",
        )

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse(
                {
                    "timezone": getattr(request.state, "geo_timezone", None),
                }
            )

        # Test with CF-Connecting-IP header
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"CF-Connecting-IP": "1.1.1.1"})

        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "Asia/Tokyo"
        mock_geoip_service.get_geo_info.assert_called_once_with("1.1.1.1")

    @pytest.mark.asyncio
    async def test_fallback_to_client_host(self):
        """Test that middleware falls back to request.client.host if no headers."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = None  # Local IP not in database

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse({"ok": True})

        # Test without headers (will use client.host from test client)
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_uses_dev_override_ip_when_set(self):
        """Test that middleware uses DEV_OVERRIDE_IP in development."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/Los_Angeles",
            country="US",
            city="Los Angeles",
        )

        # Add middleware with dev override IP
        app.add_middleware(
            GeoIPMiddleware, geoip_service=mock_geoip_service, dev_override_ip="8.8.4.4"
        )

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse(
                {
                    "timezone": getattr(request.state, "geo_timezone", None),
                }
            )

        # Test - should use dev override IP even with headers
        from httpx import ASGITransport, AsyncClient

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
    async def test_handles_geo_lookup_failure_gracefully(self):
        """Test that middleware handles geo lookup failures without crashing."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service to return None (lookup failure)
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = None

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse(
                {
                    "timezone": getattr(request.state, "geo_timezone", None),
                    "country": getattr(request.state, "geo_country", None),
                    "city": getattr(request.state, "geo_city", None),
                }
            )

        # Test with IP that's not in database
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "192.168.1.1"})

        # Should succeed with None values
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None

    @pytest.mark.asyncio
    async def test_handles_geo_service_exception_gracefully(self):
        """Test that middleware handles geo service exceptions without crashing."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service to raise exception
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.side_effect = Exception("Database error")

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse({"ok": True})

        # Test - should not crash
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test", headers={"X-Real-IP": "8.8.8.8"})

        # Should succeed even though geo lookup failed
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_header_priority_order(self):
        """Test that middleware checks headers in correct priority order."""
        from api.middleware import GeoIPMiddleware

        app = FastAPI()

        # Mock GeoIP service
        mock_geoip_service = Mock()
        mock_geoip_service.get_geo_info.return_value = GeoInfo(
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        # Add middleware
        app.add_middleware(GeoIPMiddleware, geoip_service=mock_geoip_service)

        # Add test route
        @app.get("/test")
        async def test_route(request: Request):
            return JSONResponse({"ok": True})

        # Test with all headers - X-Real-IP should take priority
        from httpx import ASGITransport, AsyncClient

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


class TestAccessLogMiddleware:
    """Tests for access log middleware with request timing."""

    @pytest.mark.asyncio
    async def test_logs_request_with_timing(self):
        """Test that middleware logs requests with method, path, status_code, and duration_ms."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()
        mock_logger = Mock()

        # Add middleware with mock logger
        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        # Check the event message (% formatting: "%s %s", method, path)
        assert call_args[0][0] == "%s %s"
        assert call_args[0][1] == "GET"
        assert call_args[0][2] == "/test"

        # Check kwargs
        kwargs = call_args[1]
        assert kwargs["status_code"] == 200
        assert "duration_ms" in kwargs
        assert kwargs["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_logs_error_responses_with_timing(self):
        """Test that error responses are also logged with timing."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/error")
        async def error_route():
            raise HTTPException(status_code=500, detail="Server error")

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/error")

        assert response.status_code == 500

        # Verify logger was called with 500 status
        mock_logger.info.assert_called_once()
        kwargs = mock_logger.info.call_args[1]
        assert kwargs["status_code"] == 500
        assert "duration_ms" in kwargs

    @pytest.mark.asyncio
    async def test_duration_reflects_actual_processing_time(self):
        """Test that duration_ms reflects actual request processing time."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/slow")
        async def slow_route():
            await asyncio.sleep(0.05)  # 50ms delay
            return JSONResponse({"ok": True})

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/slow")

        kwargs = mock_logger.info.call_args[1]
        # Duration should be at least 50ms
        assert kwargs["duration_ms"] >= 50

    @pytest.mark.asyncio
    async def test_uses_default_logger_when_none_provided(self):
        """Test that middleware uses module logger when none is provided."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()

        # Add middleware without logger - should not raise
        app.add_middleware(AccessLogMiddleware)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_client_ip_from_headers(self):
        """Test that middleware logs client IP from X-Real-IP header."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test", headers={"X-Real-IP": "1.2.3.4"})

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["client_ip"] == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_logs_multiple_requests(self):
        """Test that middleware correctly logs multiple sequential requests."""
        from api.middleware import AccessLogMiddleware

        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/first")
        async def first_route():
            return JSONResponse({"route": "first"})

        @app.post("/second")
        async def second_route():
            return JSONResponse({"route": "second"})

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/first")
            await client.post("/second")

        assert mock_logger.info.call_count == 2

        # Check first call (% formatting: "%s %s", method, path)
        first_call = mock_logger.info.call_args_list[0]
        assert first_call[0][1] == "GET"
        assert first_call[0][2] == "/first"

        # Check second call
        second_call = mock_logger.info.call_args_list[1]
        assert second_call[0][1] == "POST"
        assert second_call[0][2] == "/second"
