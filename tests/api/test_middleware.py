"""Tests for API middleware."""

import asyncio
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from api.middleware import (
    AccessLogMiddleware,
    LocalhostBlockerMiddleware,
    RateLimitMiddleware,
)
from leadr.infra.cache.adapters.memory import InMemoryCache


class TestAccessLogMiddleware:
    """Tests for access log middleware with request timing."""

    @pytest.mark.asyncio
    async def test_logs_request_with_timing(self):
        """Test that middleware logs requests with method, path, status_code, and duration_ms."""
        app = FastAPI()
        mock_logger = Mock()

        # Add middleware with mock logger
        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

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
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/error")
        async def error_route():
            raise HTTPException(status_code=500, detail="Server error")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/error")

        assert response.status_code == 500

        # Verify logger.error was called for 500 status
        mock_logger.error.assert_called_once()
        kwargs = mock_logger.error.call_args[1]
        assert kwargs["status_code"] == 500
        assert "duration_ms" in kwargs

    @pytest.mark.asyncio
    async def test_duration_reflects_actual_processing_time(self):
        """Test that duration_ms reflects actual request processing time."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/slow")
        async def slow_route():
            await asyncio.sleep(0.05)  # 50ms delay
            return JSONResponse({"ok": True})

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
        app = FastAPI()

        # Add middleware without logger - should not raise
        app.add_middleware(AccessLogMiddleware)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_client_ip_from_headers(self):
        """Test that middleware logs client IP from X-Real-IP header."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

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
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/first")
        async def first_route():
            return JSONResponse({"route": "first"})

        @app.post("/second")
        async def second_route():
            return JSONResponse({"route": "second"})

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

    @pytest.mark.asyncio
    async def test_logs_leadr_client_header(self):
        """Test that middleware logs LEADR-Client header as structured field."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get(
                "/test",
                headers={
                    "LEADR-Client": "unity-sdk; v=1.2.0; runtime=mono; platform=windows; arch=x64"
                },
            )

        kwargs = mock_logger.info.call_args[1]
        assert (
            kwargs["leadr_client"] == "unity-sdk; v=1.2.0; runtime=mono; platform=windows; arch=x64"
        )

    @pytest.mark.asyncio
    async def test_logs_user_agent_header(self):
        """Test that middleware logs User-Agent header as structured field."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test", headers={"User-Agent": "MyGame/1.0"})

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["user_agent"] == "MyGame/1.0"

    @pytest.mark.asyncio
    async def test_logs_none_when_leadr_client_absent(self):
        """Test that middleware logs None when LEADR-Client header is absent."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["leadr_client"] is None

    @pytest.mark.asyncio
    async def test_logs_none_when_user_agent_absent(self):
        """Test that middleware logs None when User-Agent header is absent."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test", headers={"User-Agent": ""})

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["user_agent"] is None

    @pytest.mark.asyncio
    async def test_truncates_long_leadr_client_header(self):
        """Test that LEADR-Client values exceeding 256 chars are truncated."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        long_value = "a" * 500

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test", headers={"LEADR-Client": long_value})

        kwargs = mock_logger.info.call_args[1]
        assert len(kwargs["leadr_client"]) == 256

    @pytest.mark.asyncio
    async def test_truncates_long_user_agent_header(self):
        """Test that User-Agent values exceeding 256 chars are truncated."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        long_value = "b" * 500

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test", headers={"User-Agent": long_value})

        kwargs = mock_logger.info.call_args[1]
        assert len(kwargs["user_agent"]) == 256

    @pytest.mark.asyncio
    async def test_logs_account_id_from_request_state(self):
        """Test that middleware logs account_id when set on request.state by a dependency."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route(request: Request):
            request.state.account_id = "acc_123"
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["account_id"] == "acc_123"
        assert kwargs["game_id"] is None

    @pytest.mark.asyncio
    async def test_logs_account_id_and_game_id_from_request_state(self):
        """Test that middleware logs both account_id and game_id when set on request.state."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route(request: Request):
            request.state.account_id = "acc_123"
            request.state.game_id = "game_456"
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["account_id"] == "acc_123"
        assert kwargs["game_id"] == "game_456"

    @pytest.mark.asyncio
    async def test_logs_none_for_account_and_game_when_state_not_set(self):
        """Test that middleware logs None for account_id and game_id on unauthenticated routes."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["account_id"] is None
        assert kwargs["game_id"] is None

    @pytest.mark.asyncio
    async def test_leadr_client_malformed_does_not_crash(self):
        """Test that malformed LEADR-Client header does not crash the middleware."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/test",
                headers={"LEADR-Client": ";;;===;;;===&&&***" * 10},
            )

        assert response.status_code == 200
        kwargs = mock_logger.info.call_args[1]
        assert "leadr_client" in kwargs

    @pytest.mark.asyncio
    async def test_logs_query_string(self):
        """Test that middleware logs query string as qs field."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test?foo=bar&baz=qux")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["qs"] == "foo=bar&baz=qux"

    @pytest.mark.asyncio
    async def test_logs_none_when_no_query_string(self):
        """Test that middleware logs None when no query string present."""
        app = FastAPI()
        mock_logger = Mock()

        app.add_middleware(AccessLogMiddleware, logger=mock_logger)

        @app.get("/test")
        async def test_route():
            return JSONResponse({"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/test")

        kwargs = mock_logger.info.call_args[1]
        assert kwargs["qs"] is None


class TestLocalhostBlockerMiddleware:
    """Tests for localhost blocking middleware."""

    @pytest.mark.asyncio
    async def test_blocks_localhost_on_non_health_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Localhost requests to non-health paths should be blocked."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "secret"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 403
        assert response.json() == {"error": "Forbidden"}

    @pytest.mark.asyncio
    async def test_allows_localhost_on_health_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Localhost requests to health endpoints should be allowed."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/v1/health")
        async def health_route():
            return JSONResponse({"status": "ok"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/v1/health", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_localhost_on_health_live_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Localhost requests to /v1/health/live should be allowed."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/v1/health/live")
        async def health_live_route():
            return JSONResponse({"status": "ok"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/v1/health/live", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_localhost_on_root_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Localhost requests to root path should be allowed."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/")
        async def root_route():
            return JSONResponse({"message": "LEADR API"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_non_localhost_traffic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-localhost traffic should pass through."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "public"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "8.8.8.8"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_blocking_in_test_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Localhost blocking should be skipped in TEST environment."""
        monkeypatch.setattr("api.middleware.settings.ENV", "TEST")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "test"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_blocking_in_dev_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Localhost blocking should be skipped in DEV environment."""
        monkeypatch.setattr("api.middleware.settings.ENV", "DEV")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "dev"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "127.0.0.1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_ipv6_localhost(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """IPv6 localhost (::1) should also be blocked."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")

        app = FastAPI()
        app.add_middleware(LocalhostBlockerMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "secret"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "::1"})

        assert response.status_code == 403


class TestRateLimitMiddleware:
    """Tests for 4xx-based rate limiting middleware."""

    @pytest.fixture(autouse=True)
    def reset_cache(self) -> None:
        """Reset the singleton cache before each test."""
        InMemoryCache.reset_instance()

    @pytest.mark.asyncio
    async def test_allows_normal_requests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Normal successful requests should pass through."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", True)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/data")
        async def data_route():
            return JSONResponse({"data": "ok"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/data", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_after_threshold_4xx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """IP should be blocked after threshold consecutive 4xx responses."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", True)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_4XX_THRESHOLD", 3)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 60)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_MAX_BLOCK_SECONDS", 3600)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/not-found")
        async def not_found_route():
            return JSONResponse({"error": "not found"}, status_code=404)

        @app.get("/ok")
        async def ok_route():
            return JSONResponse({"status": "ok"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            # Generate threshold 4xx responses
            for _ in range(3):
                await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})

            # Next request should be blocked
            response = await client.get("/ok", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 429
        assert response.json() == {"error": "Too many requests"}
        assert response.headers.get("Retry-After") == "60"

    @pytest.mark.asyncio
    async def test_success_resets_counter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful responses should reset the 4xx counter."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", True)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_4XX_THRESHOLD", 3)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/not-found")
        async def not_found_route():
            return JSONResponse({"error": "not found"}, status_code=404)

        @app.get("/ok")
        async def ok_route():
            return JSONResponse({"status": "ok"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            # Generate some 4xx responses (below threshold)
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})

            # Success resets counter
            await client.get("/ok", headers={"X-Real-IP": "1.2.3.4"})

            # Should be able to do more 4xx without being blocked
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})

            # Still not blocked (reset after success)
            response = await client.get("/ok", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_in_test_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rate limiting should be skipped in TEST environment."""
        monkeypatch.setattr("api.middleware.settings.ENV", "TEST")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", True)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_4XX_THRESHOLD", 1)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/not-found")
        async def not_found_route():
            return JSONResponse({"error": "not found"}, status_code=404)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            # Even with threshold=1, should not be blocked in TEST
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})
            response = await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 404  # Not 429

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rate limiting should be skipped when RATELIMIT_ENABLED=False."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", False)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_4XX_THRESHOLD", 1)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/not-found")
        async def not_found_route():
            return JSONResponse({"error": "not found"}, status_code=404)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})
            response = await client.get("/not-found", headers={"X-Real-IP": "1.2.3.4"})

        assert response.status_code == 404  # Not 429

    @pytest.mark.asyncio
    async def test_different_ips_tracked_separately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Different IPs should have separate counters."""
        monkeypatch.setattr("api.middleware.settings.ENV", "PROD")
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_ENABLED", True)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_4XX_THRESHOLD", 2)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_INITIAL_BLOCK_SECONDS", 60)
        monkeypatch.setattr("api.middleware.settings.RATELIMIT_MAX_BLOCK_SECONDS", 3600)

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/not-found")
        async def not_found_route():
            return JSONResponse({"error": "not found"}, status_code=404)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            # IP 1 hits threshold
            await client.get("/not-found", headers={"X-Real-IP": "1.1.1.1"})
            await client.get("/not-found", headers={"X-Real-IP": "1.1.1.1"})

            # IP 1 is blocked
            response1 = await client.get("/not-found", headers={"X-Real-IP": "1.1.1.1"})

            # IP 2 is not blocked
            response2 = await client.get("/not-found", headers={"X-Real-IP": "2.2.2.2"})

        assert response1.status_code == 429
        assert response2.status_code == 404
