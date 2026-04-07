"""Database backup utilities for LEADR.

Creates a pg_dump backup in custom format and uploads it to S3-compatible
object storage along with a JSON manifest file.

Can be run as a module or imported by other packages (e.g. leadr-cloud).

Usage:
    uv run python -m leadr.common.utils.backup
    uv run python -m leadr.common.utils.backup --local /path/to/backup/dir

Options:
    --local <dir>   Store backup files locally instead of uploading to object storage.
                    Skips upload configuration validation. Creates the directory if needed.

Environment Variables (configured in .env):
    BACKUP_ENABLED: Enable/disable backups (default: false)
    BACKUP_STORAGE_BUCKET: Object storage bucket name
    BACKUP_STORAGE_PREFIX: Key prefix within the bucket (default: "leadr-backups")
    BACKUP_STORAGE_ENDPOINT_URL: Endpoint for S3-compatible providers (Hetzner, R2, MinIO)
    BACKUP_STORAGE_REGION: Storage region
    BACKUP_STORAGE_ACCESS_KEY_ID: Access key for object storage
    BACKUP_STORAGE_SECRET_ACCESS_KEY: Secret key for object storage
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3

from leadr.config import settings

logger = logging.getLogger(__name__)


def build_object_key(
    prefix: str, db_name: str, timestamp: datetime, ext: str, *, env: str | None = None
) -> str:
    """Build the object storage key for a backup file.

    Structure: {prefix}/{YYYY}/{MM}/{db_name}_{YYYYMMDD}T{HHMMSS}Z[.{env}].{ext}
    """
    ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    year = timestamp.strftime("%Y")
    month = timestamp.strftime("%m")
    env_part = f".{env}" if env else ""
    return f"{prefix}/{year}/{month}/{db_name}_{ts_str}{env_part}.{ext}"


def compute_md5(file_path: Path) -> str:
    """Compute the MD5 hex digest of a file."""
    md5 = hashlib.md5()  # noqa: S324
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def build_manifest(
    *,
    timestamp: datetime,
    db_name: str,
    db_host: str,
    db_port: int,
    backup_filename: str,
    backup_size_bytes: int,
    backup_md5: str,
    pg_dump_version: str,
    duration_seconds: float,
    env: str | None = None,
) -> dict[str, Any]:
    """Build the JSON manifest for a backup."""
    manifest: dict[str, Any] = {
        "version": 1,
        "timestamp": timestamp.isoformat(),
        "database": {
            "name": db_name,
            "host": db_host,
            "port": db_port,
        },
        "backup_file": backup_filename,
        "backup_format": "custom",
        "backup_size_bytes": backup_size_bytes,
        "backup_md5": backup_md5,
        "pg_dump_version": pg_dump_version,
        "duration_seconds": duration_seconds,
        "artifacts": [],
    }
    if env:
        manifest["env"] = env
    return manifest


def validate_backup_config(
    *,
    bucket: str,
    access_key_id: str,
    secret_access_key: str,
) -> None:
    """Validate that required backup configuration is present."""
    if not bucket:
        raise ValueError("BACKUP_STORAGE_BUCKET must be set when BACKUP_ENABLED=true")
    if not access_key_id:
        raise ValueError("BACKUP_STORAGE_ACCESS_KEY_ID must be set when BACKUP_ENABLED=true")
    if not secret_access_key:
        raise ValueError("BACKUP_STORAGE_SECRET_ACCESS_KEY must be set when BACKUP_ENABLED=true")


def get_pg_dump_version() -> str:
    """Get the pg_dump version string."""
    result = subprocess.run(
        ["pg_dump", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def upload_to_storage(
    *,
    dump_path: Path,
    manifest_path: Path,
    dump_key: str,
    manifest_key: str,
) -> None:
    """Upload backup files to S3-compatible object storage."""
    logger.info("Uploading to %s/%s", settings.BACKUP_STORAGE_BUCKET, dump_key)

    s3_client_kwargs: dict[str, Any] = {
        "aws_access_key_id": settings.BACKUP_STORAGE_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.BACKUP_STORAGE_SECRET_ACCESS_KEY,
    }
    if settings.BACKUP_STORAGE_ENDPOINT_URL:
        s3_client_kwargs["endpoint_url"] = settings.BACKUP_STORAGE_ENDPOINT_URL
    if settings.BACKUP_STORAGE_REGION:
        s3_client_kwargs["region_name"] = settings.BACKUP_STORAGE_REGION

    s3 = boto3.client("s3", **s3_client_kwargs)

    s3.upload_file(
        Filename=str(dump_path),
        Bucket=settings.BACKUP_STORAGE_BUCKET,
        Key=dump_key,
    )
    logger.info("Uploaded dump: %s", dump_key)

    s3.upload_file(
        Filename=str(manifest_path),
        Bucket=settings.BACKUP_STORAGE_BUCKET,
        Key=manifest_key,
    )
    logger.info("Uploaded manifest: %s", manifest_key)


def run_backup(*, local_dir: Path | None = None) -> None:
    """Run the database backup process."""
    if not settings.BACKUP_ENABLED:
        logger.info("Backups disabled (BACKUP_ENABLED=false), skipping")
        return

    if not local_dir:
        validate_backup_config(
            bucket=settings.BACKUP_STORAGE_BUCKET,
            access_key_id=settings.BACKUP_STORAGE_ACCESS_KEY_ID,
            secret_access_key=settings.BACKUP_STORAGE_SECRET_ACCESS_KEY,
        )

    timestamp = datetime.now(UTC)
    db_host = settings.DB_HOST_DIRECT or settings.DB_HOST
    db_name = settings.DB_NAME
    env = settings.ENV.lower()

    logger.info("Starting database backup")
    logger.info("Database: %s@%s:%d/%s", settings.DB_USER, db_host, settings.DB_PORT, db_name)
    logger.info("Environment: %s", env)

    # Get pg_dump version
    pg_dump_version = get_pg_dump_version()
    logger.info("pg_dump version: %s", pg_dump_version)

    # Build object keys
    dump_key = build_object_key(
        prefix=settings.BACKUP_STORAGE_PREFIX,
        db_name=db_name,
        timestamp=timestamp,
        ext="dump",
        env=env,
    )
    manifest_key = build_object_key(
        prefix=settings.BACKUP_STORAGE_PREFIX,
        db_name=db_name,
        timestamp=timestamp,
        ext="manifest.json",
        env=env,
    )
    dump_filename = Path(dump_key).name
    manifest_filename = Path(manifest_key).name

    def _create_backup(work_dir: Path) -> None:
        dump_path = work_dir / dump_filename
        manifest_path = work_dir / manifest_filename

        # Run pg_dump
        start_time = time.monotonic()
        pg_dump_cmd = [
            "pg_dump",
            "-Fc",
            "-h",
            db_host,
            "-p",
            str(settings.DB_PORT),
            "-U",
            settings.DB_USER,
            "-d",
            db_name,
            "-f",
            str(dump_path),
        ]

        pg_env = None
        if settings.DB_PASSWORD:
            pg_env = {**os.environ, "PGPASSWORD": settings.DB_PASSWORD}

        logger.info("Running pg_dump...")
        subprocess.run(pg_dump_cmd, check=True, env=pg_env)
        duration = time.monotonic() - start_time

        backup_size = dump_path.stat().st_size
        logger.info("pg_dump completed in %.1fs, size: %d bytes", duration, backup_size)

        # Compute checksum
        backup_md5 = compute_md5(dump_path)
        logger.info("MD5: %s", backup_md5)

        # Build and write manifest
        manifest = build_manifest(
            timestamp=timestamp,
            db_name=db_name,
            db_host=db_host,
            db_port=settings.DB_PORT,
            backup_filename=dump_filename,
            backup_size_bytes=backup_size,
            backup_md5=backup_md5,
            pg_dump_version=pg_dump_version,
            duration_seconds=round(duration, 2),
            env=env,
        )
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # --- Future: Artifact Backups ---
        # When ready, add backup logic here for:
        # - User-generated content (UGC) in object storage
        # - JSON blobs / config exports
        # - Other connected artefacts
        # Each artifact backup should append to manifest["artifacts"]

        if local_dir:
            logger.info("Local mode: files saved to %s", work_dir)
        else:
            upload_to_storage(
                dump_path=dump_path,
                manifest_path=manifest_path,
                dump_key=dump_key,
                manifest_key=manifest_key,
            )

    if local_dir:
        local_dir.mkdir(parents=True, exist_ok=True)
        _create_backup(local_dir)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_backup(Path(tmpdir))

    logger.info("Backup completed successfully")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="LEADR database backup")
    parser.add_argument(
        "--local",
        type=Path,
        default=None,
        help="Store backup files locally at the given directory instead of uploading",
    )
    args = parser.parse_args()

    try:
        run_backup(local_dir=args.local)
    except Exception as e:
        logger.exception("Backup failed: %s", str(e))
        sys.exit(1)
