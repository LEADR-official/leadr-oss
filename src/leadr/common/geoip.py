"""GeoIP service for IP address geolocation using MaxMind databases."""

import logging
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import maxminddb

logger = logging.getLogger(__name__)


@dataclass
class GeoInfo:
    """Geolocation information extracted from IP address.

    Attributes:
        timezone: IANA timezone identifier (e.g., 'America/New_York')
        country: ISO country code (e.g., 'US')
        city: City name (e.g., 'New York')
    """

    timezone: str | None
    country: str | None
    city: str | None


class GeoIPService:
    """Service for IP address geolocation using MaxMind GeoLite2 databases.

    This service downloads and manages MaxMind GeoLite2 databases for IP geolocation.
    Databases are cached locally and refreshed periodically.

    Example:
        >>> service = GeoIPService(
        ...     account_id="12345",
        ...     license_key="your_key",
        ...     city_db_url="https://download.maxmind.com/...",
        ...     country_db_url="https://download.maxmind.com/...",
        ...     database_path=Path(".geoip"),
        ...     refresh_days=7,
        ... )
        >>> await service.initialize()
        >>> geo_info = service.get_geo_info("8.8.8.8")
        >>> print(geo_info.country)
        'US'
    """

    def __init__(
        self,
        account_id: str,
        license_key: str,
        city_db_url: str,
        country_db_url: str,
        database_path: Path,
        refresh_days: int = 7,
    ):
        """Initialize GeoIP service with configuration.

        Args:
            account_id: MaxMind account ID for basic auth
            license_key: MaxMind license key for basic auth
            city_db_url: URL to download GeoLite2 City database (tar.gz)
            country_db_url: URL to download GeoLite2 Country database (tar.gz)
            database_path: Directory path to store database files
            refresh_days: Number of days before refreshing databases (default: 7)
        """
        self.account_id = account_id
        self.license_key = license_key
        self.city_db_url = city_db_url
        self.country_db_url = country_db_url
        self.database_path = database_path
        self.refresh_days = refresh_days

        # Database readers (initialized in initialize())
        self._city_reader: maxminddb.Reader | None = None
        self._country_reader: maxminddb.Reader | None = None

    async def initialize(self) -> None:
        """Initialize the GeoIP service by downloading and loading databases.

        This method:
        1. Creates the database directory if it doesn't exist
        2. Downloads databases if they don't exist or are stale
        3. Extracts tar.gz files to get .mmdb files
        4. Opens database readers

        Errors are logged but not raised - the service will work without databases
        (get_geo_info will return None).
        """
        try:
            # Ensure database directory exists
            self.database_path.mkdir(parents=True, exist_ok=True)

            # Download databases if needed
            await self._ensure_databases()

            # Open database readers
            city_db_path = self.database_path / "GeoLite2-City.mmdb"
            country_db_path = self.database_path / "GeoLite2-Country.mmdb"

            if city_db_path.exists():
                self._city_reader = maxminddb.open_database(str(city_db_path))
                logger.info("Loaded GeoLite2 City database from %s", city_db_path)

            if country_db_path.exists():
                self._country_reader = maxminddb.open_database(str(country_db_path))
                logger.info("Loaded GeoLite2 Country database from %s", country_db_path)

        except Exception:
            logger.exception("Failed to initialize GeoIP service")

    async def _ensure_databases(self) -> None:
        """Download databases if they don't exist or are stale."""
        city_db_path = self.database_path / "GeoLite2-City.mmdb"
        country_db_path = self.database_path / "GeoLite2-Country.mmdb"

        # Check if databases need download
        city_needs_download = self._needs_download(city_db_path)
        country_needs_download = self._needs_download(country_db_path)

        if not city_needs_download and not country_needs_download:
            logger.debug("GeoIP databases are fresh, skipping download")
            return

        # Download databases with basic auth
        async with httpx.AsyncClient(
            auth=(self.account_id, self.license_key),
            timeout=300.0,  # 5 minutes for large files
        ) as client:
            if city_needs_download:
                logger.info("Downloading GeoLite2 City database...")
                await self._download_and_extract(client, self.city_db_url, "GeoLite2-City.mmdb")

            if country_needs_download:
                logger.info("Downloading GeoLite2 Country database...")
                await self._download_and_extract(
                    client, self.country_db_url, "GeoLite2-Country.mmdb"
                )

    def _needs_download(self, db_path: Path) -> bool:
        """Check if a database file needs to be downloaded.

        Args:
            db_path: Path to the database file

        Returns:
            True if the file doesn't exist or is stale, False otherwise
        """
        if not db_path.exists():
            return True

        # Check if file is stale
        file_age = datetime.now(UTC) - datetime.fromtimestamp(db_path.stat().st_mtime, tz=UTC)
        return file_age > timedelta(days=self.refresh_days)

    async def _download_and_extract(
        self, client: httpx.AsyncClient, url: str, target_filename: str
    ) -> None:
        """Download a tar.gz database file and extract the .mmdb file.

        Args:
            client: HTTP client with auth configured
            url: URL to download from
            target_filename: Filename to save the extracted .mmdb as
        """
        # Download tar.gz file
        response = await client.get(url)
        response.raise_for_status()

        # Save to temporary tar.gz file
        tar_gz_path = self.database_path / f"{target_filename}.tar.gz"
        tar_gz_path.write_bytes(response.content)

        # Extract .mmdb file from tar.gz
        with tarfile.open(tar_gz_path, "r:gz") as tar:
            # Find the .mmdb file in the archive
            mmdb_members = [m for m in tar.getmembers() if m.name.endswith(".mmdb")]
            if not mmdb_members:
                logger.error("No .mmdb file found in %s", tar_gz_path)
                return

            # Extract the .mmdb file
            mmdb_member = mmdb_members[0]
            mmdb_file = tar.extractfile(mmdb_member)
            if mmdb_file is None:
                logger.error("Failed to extract %s from %s", mmdb_member.name, tar_gz_path)
                return

            # Save to target location
            target_path = self.database_path / target_filename
            target_path.write_bytes(mmdb_file.read())
            logger.info("Extracted %s from %s", target_filename, tar_gz_path)

        # Clean up tar.gz file
        tar_gz_path.unlink()

    def get_geo_info(self, ip_address: str) -> GeoInfo | None:
        """Look up geolocation information for an IP address.

        Args:
            ip_address: IP address to look up (e.g., '8.8.8.8')

        Returns:
            GeoInfo with timezone, country, and city, or None if lookup fails
        """
        if self._city_reader is None:
            return None

        try:
            # Look up IP in City database (includes country info)
            result = self._city_reader.get(ip_address)
            if result is None or not isinstance(result, dict):
                return None

            # Extract geo information with type checking
            timezone: str | None = None
            country: str | None = None
            city: str | None = None

            location = result.get("location")
            if isinstance(location, dict):
                tz = location.get("time_zone")
                timezone = str(tz) if tz is not None and not isinstance(tz, dict) else None

            country_data = result.get("country")
            if isinstance(country_data, dict):
                iso_code = country_data.get("iso_code")
                country = (
                    str(iso_code)
                    if iso_code is not None and not isinstance(iso_code, dict)
                    else None
                )

            city_data = result.get("city")
            if isinstance(city_data, dict):
                names = city_data.get("names")
                if isinstance(names, dict):
                    city_name = names.get("en")
                    city = (
                        str(city_name)
                        if city_name is not None and not isinstance(city_name, dict)
                        else None
                    )

            return GeoInfo(timezone=timezone, country=country, city=city)

        except Exception:
            logger.exception("Failed to look up IP address: %s", ip_address)
            return None

    def close(self) -> None:
        """Close database readers and release resources."""
        if self._city_reader is not None:
            self._city_reader.close()
            self._city_reader = None

        if self._country_reader is not None:
            self._country_reader.close()
            self._country_reader = None
