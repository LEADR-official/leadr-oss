"""Tests for GeoIP service."""

import io
import os
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import maxminddb
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

            # Mock database reader (used both as context manager in validation and directly)
            mock_reader = MagicMock()
            mock_open_db.return_value = mock_reader
            mock_reader.__enter__ = Mock(return_value=mock_reader)
            mock_reader.__exit__ = Mock(return_value=False)

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
    async def test_initialize_skips_download_when_disabled(self, geoip_config):
        """Test that initialize skips download when download_enabled=False."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Mock database reader
            mock_reader = Mock()
            mock_open_db.return_value = mock_reader

            # Create service with download_enabled=False
            service = GeoIPService(**geoip_config, download_enabled=False)
            await service.initialize()

            # Verify no downloads occurred even though databases don't exist
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_loads_existing_databases_when_download_disabled(self, geoip_config):
        """Test that initialize loads existing databases even when download_enabled=False."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database") as mock_open_db,
        ):
            # Create fake database files
            city_db_path = geoip_config["database_path"] / "GeoLite2-City.mmdb"
            country_db_path = geoip_config["database_path"] / "GeoLite2-Country.mmdb"
            city_db_path.write_bytes(b"existing_db")
            country_db_path.write_bytes(b"existing_db")

            # Mock database reader
            mock_reader = Mock()
            mock_reader.get.return_value = {
                "city": {"names": {"en": "New York"}},
                "country": {"iso_code": "US"},
                "location": {"time_zone": "America/New_York"},
            }
            mock_open_db.return_value = mock_reader

            # Create service with download_enabled=False
            service = GeoIPService(**geoip_config, download_enabled=False)
            await service.initialize()

            # Verify no downloads occurred
            mock_client_class.assert_not_called()

            # Verify databases were loaded and can be used
            geo_info = service.get_geo_info("8.8.8.8")
            assert geo_info is not None
            assert geo_info.country == "US"

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

            # Mock database reader (used both as context manager in validation and directly)
            mock_reader = MagicMock()
            mock_open_db.return_value = mock_reader
            mock_reader.__enter__ = Mock(return_value=mock_reader)
            mock_reader.__exit__ = Mock(return_value=False)

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
    async def test_initialize_handles_429_rate_limit(self, geoip_config):
        """Test that initialize handles 429 rate limit errors gracefully."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database"),
        ):
            # Mock HTTP response with 429 status
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limited",
                request=Mock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            service = GeoIPService(**geoip_config)

            # Initialize should not raise exception even with 429
            await service.initialize()

            # Service should still be usable but return None for lookups
            geo_info = service.get_geo_info("8.8.8.8")
            assert geo_info is None

    @pytest.mark.asyncio
    async def test_initialize_handles_http_error(self, geoip_config):
        """Test that initialize handles HTTP errors (500, etc) gracefully."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database"),
        ):
            # Mock HTTP response with 500 status
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=Mock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            service = GeoIPService(**geoip_config)

            # Initialize should not raise exception even with HTTP error
            await service.initialize()

            # Service should still be usable but return None for lookups
            geo_info = service.get_geo_info("8.8.8.8")
            assert geo_info is None

    @pytest.mark.asyncio
    async def test_initialize_handles_network_error(self, geoip_config):
        """Test that initialize handles network errors gracefully."""
        with (
            patch("leadr.common.geoip.httpx.AsyncClient") as mock_client_class,
            patch("leadr.common.geoip.maxminddb.open_database"),
        ):
            # Mock HTTP client to raise network error
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            service = GeoIPService(**geoip_config)

            # Initialize should not raise exception even with network error
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


class TestGetGeoInfoInvalidDatabase:
    """Tests for get_geo_info handling of corrupted databases."""

    def test_returns_none_on_invalid_database_error(self, geoip_config) -> None:
        service = GeoIPService(**geoip_config)
        mock_reader = MagicMock()
        mock_reader.get.side_effect = maxminddb.InvalidDatabaseError(
            "Invalid data type arguments: 95"
        )
        service._city_reader = mock_reader

        result = service.get_geo_info("8.8.8.8")

        assert result is None

    def test_disables_reader_on_invalid_database_error(self, geoip_config) -> None:
        service = GeoIPService(**geoip_config)
        mock_reader = MagicMock()
        mock_reader.get.side_effect = maxminddb.InvalidDatabaseError(
            "Invalid data type arguments: 95"
        )
        service._city_reader = mock_reader

        service.get_geo_info("8.8.8.8")

        assert service._city_reader is None

    def test_deletes_corrupt_db_file_on_invalid_database_error(self, tmp_path: Path) -> None:
        config = {
            "account_id": "test",
            "license_key": "test",
            "city_db_url": "http://example.com/city",
            "country_db_url": "http://example.com/country",
            "database_path": tmp_path,
        }
        service = GeoIPService(**config)
        mock_reader = MagicMock()
        mock_reader.get.side_effect = maxminddb.InvalidDatabaseError(
            "Invalid data type arguments: 95"
        )
        service._city_reader = mock_reader

        # Create a fake corrupt db file on disk
        corrupt_file = tmp_path / "GeoLite2-City.mmdb"
        corrupt_file.write_bytes(b"corrupt data")
        assert corrupt_file.exists()

        service.get_geo_info("8.8.8.8")

        assert not corrupt_file.exists()

    def test_subsequent_calls_skip_lookup_after_corruption(self, geoip_config) -> None:
        service = GeoIPService(**geoip_config)
        mock_reader = MagicMock()
        mock_reader.get.side_effect = maxminddb.InvalidDatabaseError(
            "Invalid data type arguments: 95"
        )
        service._city_reader = mock_reader

        service.get_geo_info("8.8.8.8")
        result = service.get_geo_info("1.1.1.1")

        assert result is None
        mock_reader.get.assert_called_once()


class TestDownloadAndExtractValidation:
    """Tests for database validation after download."""

    @pytest.mark.asyncio
    async def test_corrupted_download_is_deleted(self, tmp_path: Path) -> None:
        config = {
            "account_id": "test",
            "license_key": "test",
            "city_db_url": "http://example.com/city",
            "country_db_url": "http://example.com/country",
            "database_path": tmp_path,
        }
        service = GeoIPService(**config)

        # Build a tar.gz containing a fake corrupt mmdb
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = b"not a valid mmdb file"
            info = tarfile.TarInfo(name="GeoLite2-City/GeoLite2-City.mmdb")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tar_bytes = buf.getvalue()

        mock_response = MagicMock()
        mock_response.content = tar_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        await service._download_and_extract(mock_client, "http://example.com", "GeoLite2-City.mmdb")

        target_path = tmp_path / "GeoLite2-City.mmdb"
        assert not target_path.exists()

    @pytest.mark.asyncio
    async def test_validation_checks_multiple_ips(self, tmp_path: Path) -> None:
        """Database that passes first IP but fails on subsequent IPs should be deleted."""
        config = {
            "account_id": "test",
            "license_key": "test",
            "city_db_url": "http://example.com/city",
            "country_db_url": "http://example.com/country",
            "database_path": tmp_path,
        }
        service = GeoIPService(**config)

        # Create a tar.gz with a fake mmdb that we'll mock validation for
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = b"fake mmdb content"
            info = tarfile.TarInfo(name="GeoLite2-City/GeoLite2-City.mmdb")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tar_bytes = buf.getvalue()

        mock_response = MagicMock()
        mock_response.content = tar_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock open_database to return a reader that fails on the second IP
        call_count = 0

        def side_effect(ip: str):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise maxminddb.InvalidDatabaseError("Invalid data type arguments: 95")
            return None

        mock_reader = MagicMock()
        mock_reader.get.side_effect = side_effect
        mock_reader.__enter__ = MagicMock(return_value=mock_reader)
        mock_reader.__exit__ = MagicMock(return_value=False)

        with patch("leadr.common.geoip.maxminddb.open_database", return_value=mock_reader):
            await service._download_and_extract(
                mock_client, "http://example.com", "GeoLite2-City.mmdb"
            )

        target_path = tmp_path / "GeoLite2-City.mmdb"
        assert not target_path.exists()
