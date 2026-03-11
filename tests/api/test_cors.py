"""Tests for CORS middleware configuration."""

import pytest
from httpx import ASGITransport, AsyncClient


class TestCORSMiddleware:
    """Tests for CORS middleware behavior."""

    @pytest.mark.asyncio
    async def test_preflight_request_returns_cors_headers(self, test_app):
        """Test that OPTIONS preflight requests return appropriate CORS headers."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/sessions",
                headers={
                    "Origin": "https://example-game.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Authorization, Content-Type",
                },
            )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    @pytest.mark.asyncio
    async def test_cors_allows_any_origin(self, test_app):
        """Test that client API endpoints are accessible from any origin."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/sessions",
                headers={
                    "Origin": "https://my-indie-game.itch.io",
                    "Access-Control-Request-Method": "POST",
                },
            )

        # With allow_origins=["*"], the response should include * or echo the origin
        assert response.headers.get("access-control-allow-origin") in [
            "*",
            "https://my-indie-game.itch.io",
        ]

    @pytest.mark.asyncio
    async def test_cors_allows_authorization_header(self, test_app):
        """Test that Authorization header is allowed in CORS requests."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/scores",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Authorization",
                },
            )

        assert response.status_code == 200
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in allowed_headers

    @pytest.mark.asyncio
    async def test_cors_allows_leadr_client_nonce_header(self, test_app):
        """Test that leadr-client-nonce header is allowed for replay protection."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/scores",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "leadr-client-nonce",
                },
            )

        assert response.status_code == 200
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "leadr-client-nonce" in allowed_headers

    @pytest.mark.asyncio
    async def test_cors_headers_on_actual_request(self, test_app):
        """Test that actual cross-origin requests include CORS headers in response."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/v1/health",
                headers={"Origin": "https://example.com"},
            )

        # Should include CORS header in response (not just preflight)
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_cors_max_age_is_set(self, test_app):
        """Test that preflight response includes max-age for caching."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/sessions",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )

        # Should include max-age header
        assert "access-control-max-age" in response.headers

    @pytest.mark.asyncio
    async def test_cors_allows_required_methods(self, test_app):
        """Test that all required HTTP methods are allowed."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/client/scores",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )

        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allowed_methods
        assert "GET" in allowed_methods
        assert "PATCH" in allowed_methods

    @pytest.mark.asyncio
    async def test_cors_allows_leadr_api_key_header(self, test_app):
        """Test that leadr-api-key header is allowed for admin API authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as client:
            response = await client.options(
                "/v1/games",
                headers={
                    "Origin": "https://dashboard.example.com",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "leadr-api-key",
                },
            )

        assert response.status_code == 200
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "leadr-api-key" in allowed_headers
