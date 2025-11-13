"""Tests for GeoIP service."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from leadr.common.geoip import GeoInfo, GeoIPService


@pytest.fixture
def geoip_config():
    """Create test configuration for GeoIP service."""
    return {
        "account_id": "test_account_id",
        "license_key": "test_license_key",
        "city_db_url": "https://example.com/GeoLite2-City.tar.gz",
        "country_db_url": "https://example.com/GeoLite2-Country.tar.gz",
        "database_path": Path(tempfile.mkdtemp()),
        "refresh_days": 7,
    }


@pytest.fixture
def mock_maxmind_response():
    """Create mock MaxMind database response."""
    return {
        "city": {"names": {"en": "New York"}},
        "country": {"names": {"en": "United States"}, "iso_code": "US"},
        "location": {"time_zone": "America/New_York"},
    }


class TestGeoIPService:
    """Tests for GeoIPService."""

    @pytest.mark.asyncio
    async def test_initialize_downloads_databases(self, geoip_config):
        """Test that initialize downloads databases if they don't exist."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
            patch("leadr.common.geoip.tarfile.open") as mock_tarfile,
        ):
            # Mock HTTP client for downloads
            mock_response = Mock()
            mock_response.content = b"fake_db_content"
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock tarfile extraction
            mock_member = Mock()
            mock_member.name = "GeoLite2-City_20241113/GeoLite2-City.mmdb"
            mock_file = Mock()
            mock_file.read.return_value = b"fake_mmdb_content"
            mock_tar = MagicMock()
            mock_tar.getmembers.return_value = [mock_member]
            mock_tar.extractfile.return_value = mock_file
            mock_tar.__enter__.return_value = mock_tar
            mock_tar.__exit__.return_value = None
            mock_tarfile.return_value = mock_tar

            # Mock database reader
            mock_reader = Mock()
            mock_open_db.return_value = mock_reader

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Verify downloads occurred
            assert mock_client.get.call_count == 2
            assert mock_client.get.call_args_list[0][0][0] == geoip_config["city_db_url"]
            assert mock_client.get.call_args_list[1][0][0] == geoip_config["country_db_url"]

            # Verify database files were created
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            assert city_db_path.exists()
            assert country_db_path.exists()

    @pytest.mark.asyncio
    async def test_initialize_skips_download_for_fresh_databases(self, geoip_config):
        """Test that initialize skips download if databases are fresh."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Create fake database files with recent timestamps
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"existing_db")
            country_db_path.write_bytes(b"existing_db")

            # Mock database reader
            mock_reader = Mock()
            mock_open_db.return_value = mock_reader

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Verify no downloads occurred
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_refreshes_stale_databases(self, geoip_config):
        """Test that initialize refreshes databases older than refresh_days."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
            patch("leadr.common.geoip.tarfile.open") as mock_tarfile,
        ):
            # Create fake database files with old timestamps
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"old_db")
            country_db_path.write_bytes(b"old_db")

            # Set modification time to 10 days ago
            old_timestamp = (datetime.now(UTC) - timedelta(days=10)).timestamp()
            city_db_path.touch()
            country_db_path.touch()
            import os

            os.utime(city_db_path, (old_timestamp, old_timestamp))
            os.utime(country_db_path, (old_timestamp, old_timestamp))

            # Mock HTTP client for downloads
            mock_response = Mock()
            mock_response.content = b"new_db_content"
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock tarfile extraction
            mock_member = Mock()
            mock_member.name = "GeoLite2-City_20241113/GeoLite2-City.mmdb"
            mock_file = Mock()
            mock_file.read.return_value = b"new_mmdb_content"
            mock_tar = MagicMock()
            mock_tar.getmembers.return_value = [mock_member]
            mock_tar.extractfile.return_value = mock_file
            mock_tar.__enter__.return_value = mock_tar
            mock_tar.__exit__.return_value = None
            mock_tarfile.return_value = mock_tar

            # Mock database reader
            mock_reader = Mock()
            mock_open_db.return_value = mock_reader

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Verify downloads occurred
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_geo_info_success(self, geoip_config, mock_maxmind_response):
        """Test successful IP lookup returning geo information."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient"),
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Mock database reader
            mock_reader = Mock()
            mock_reader.get.return_value = mock_maxmind_response
            mock_open_db.return_value = mock_reader

            # Create fake database files
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"fake_db")
            country_db_path.write_bytes(b"fake_db")

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Test IP lookup
            geo_info = service.get_geo_info("8.8.8.8")

            assert geo_info is not None
            assert geo_info.timezone == "America/New_York"
            assert geo_info.country == "US"
            assert geo_info.city == "New York"

    @pytest.mark.asyncio
    async def test_get_geo_info_ip_not_found(self, geoip_config):
        """Test IP lookup when IP is not in database."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient"),
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Mock database reader returning None (IP not found)
            mock_reader = Mock()
            mock_reader.get.return_value = None
            mock_open_db.return_value = mock_reader

            # Create fake database files
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"fake_db")
            country_db_path.write_bytes(b"fake_db")

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Test IP lookup for unknown IP
            geo_info = service.get_geo_info("192.168.1.1")

            assert geo_info is None

    @pytest.mark.asyncio
    async def test_get_geo_info_invalid_ip(self, geoip_config):
        """Test IP lookup with invalid IP address."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient"),
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Mock database reader
            mock_reader = Mock()
            mock_reader.get.side_effect = ValueError("Invalid IP")
            mock_open_db.return_value = mock_reader

            # Create fake database files
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"fake_db")
            country_db_path.write_bytes(b"fake_db")

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Test IP lookup with invalid IP
            geo_info = service.get_geo_info("not-an-ip")

            assert geo_info is None

    @pytest.mark.asyncio
    async def test_get_geo_info_before_initialization(self, geoip_config):
        """Test that get_geo_info returns None if called before initialization."""
        service = GeoIPService(**geoip_config)

        # Call get_geo_info without initializing
        geo_info = service.get_geo_info("8.8.8.8")

        assert geo_info is None

    @pytest.mark.asyncio
    async def test_initialize_handles_download_failure(self, geoip_config):
        """Test that initialize handles download failures gracefully."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database"),
        ):
            # Mock HTTP client to raise exception
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Download failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            service = GeoIPService(**geoip_config)

            # Initialize should not raise exception
            await service.initialize()

            # Service should still be usable but return None for lookups
            geo_info = service.get_geo_info("8.8.8.8")
            assert geo_info is None

    @pytest.mark.asyncio
    async def test_get_geo_info_with_partial_data(self, geoip_config):
        """Test IP lookup with partial geo data (missing city or timezone)."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient"),
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Mock database reader with partial data
            partial_response = {
                "country": {"names": {"en": "United States"}, "iso_code": "US"},
                # Missing city and location data
            }
            mock_reader = Mock()
            mock_reader.get.return_value = partial_response
            mock_open_db.return_value = mock_reader

            # Create fake database files
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"fake_db")
            country_db_path.write_bytes(b"fake_db")

            service = GeoIPService(**geoip_config)
            await service.initialize()

            # Test IP lookup with partial data
            geo_info = service.get_geo_info("8.8.8.8")

            assert geo_info is not None
            assert geo_info.country == "US"
            assert geo_info.city is None
            assert geo_info.timezone is None


class TestGeoInfo:
    """Tests for GeoInfo dataclass."""

    def test_geo_info_creation(self):
        """Test GeoInfo dataclass creation."""
        geo_info = GeoInfo(
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        assert geo_info.timezone == "America/New_York"
        assert geo_info.country == "US"
        assert geo_info.city == "New York"

    def test_geo_info_with_none_values(self):
        """Test GeoInfo dataclass with None values."""
        geo_info = GeoInfo(
            timezone=None,
            country="US",
            city=None,
        )

        assert geo_info.timezone is None
        assert geo_info.country == "US"
        assert geo_info.city is None
