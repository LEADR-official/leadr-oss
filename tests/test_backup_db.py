"""Tests for the database backup script."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from leadr.common.utils.backup import (
    build_manifest,
    build_object_key,
    run_backup,
    upload_to_storage,
    validate_backup_config,
)


class TestBuildObjectKey:
    """Tests for object key path generation."""

    def test_builds_correct_key_structure(self):
        """Object key follows {prefix}/{YYYY}/{MM}/{db}_{timestamp}.ext pattern."""
        ts = datetime(2026, 4, 6, 14, 30, 45, tzinfo=UTC)
        key = build_object_key(prefix="leadr-backups", db_name="leadr", timestamp=ts, ext="dump")

        assert key == "leadr-backups/2026/04/leadr_20260406T143045Z.dump"

    def test_manifest_extension(self):
        """Manifest files use .manifest.json extension."""
        ts = datetime(2026, 1, 15, 8, 0, 0, tzinfo=UTC)
        key = build_object_key(
            prefix="my-prefix", db_name="mydb", timestamp=ts, ext="manifest.json"
        )

        assert key == "my-prefix/2026/01/mydb_20260115T080000Z.manifest.json"

    def test_single_digit_month_is_zero_padded(self):
        """Month is always two digits."""
        ts = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
        key = build_object_key(prefix="p", db_name="db", timestamp=ts, ext="dump")

        assert key == "p/2026/03/db_20260301T000000Z.dump"


class TestBuildManifest:
    """Tests for JSON manifest generation."""

    def test_manifest_structure(self):
        """Manifest contains all required fields including MD5 checksum."""
        ts = datetime(2026, 4, 6, 14, 30, 45, tzinfo=UTC)
        manifest = build_manifest(
            timestamp=ts,
            db_name="leadr",
            db_host="db.example.com",
            db_port=5432,
            backup_filename="leadr_20260406T143045Z.dump",
            backup_size_bytes=12345678,
            backup_md5="d41d8cd98f00b204e9800998ecf8427e",
            pg_dump_version="15.4",
            duration_seconds=42.5,
        )

        assert manifest["version"] == 1
        assert manifest["timestamp"] == "2026-04-06T14:30:45+00:00"
        assert manifest["database"]["name"] == "leadr"
        assert manifest["database"]["host"] == "db.example.com"
        assert manifest["database"]["port"] == 5432
        assert manifest["backup_file"] == "leadr_20260406T143045Z.dump"
        assert manifest["backup_format"] == "custom"
        assert manifest["backup_size_bytes"] == 12345678
        assert manifest["backup_md5"] == "d41d8cd98f00b204e9800998ecf8427e"
        assert manifest["pg_dump_version"] == "15.4"
        assert manifest["duration_seconds"] == 42.5
        assert manifest["artifacts"] == []

    def test_manifest_is_json_serializable(self):
        """Manifest can be serialized to JSON."""
        ts = datetime(2026, 4, 6, 14, 30, 45, tzinfo=UTC)
        manifest = build_manifest(
            timestamp=ts,
            db_name="leadr",
            db_host="localhost",
            db_port=5432,
            backup_filename="leadr_20260406T143045Z.dump",
            backup_size_bytes=100,
            backup_md5="abc123",
            pg_dump_version="16.0",
            duration_seconds=1.0,
        )

        serialized = json.dumps(manifest)
        parsed = json.loads(serialized)
        assert parsed == manifest


class TestValidateConfig:
    """Tests for backup configuration validation."""

    def test_missing_bucket_raises(self):
        """Raises ValueError when bucket is empty but backup is enabled."""
        with pytest.raises(ValueError, match="BACKUP_STORAGE_BUCKET"):
            validate_backup_config(
                bucket="",
                access_key_id="key",
                secret_access_key="secret",
            )

    def test_missing_access_key_raises(self):
        """Raises ValueError when access key is empty."""
        with pytest.raises(ValueError, match="BACKUP_STORAGE_ACCESS_KEY_ID"):
            validate_backup_config(
                bucket="my-bucket",
                access_key_id="",
                secret_access_key="secret",
            )

    def test_missing_secret_key_raises(self):
        """Raises ValueError when secret key is empty."""
        with pytest.raises(ValueError, match="BACKUP_STORAGE_SECRET_ACCESS_KEY"):
            validate_backup_config(
                bucket="my-bucket",
                access_key_id="key",
                secret_access_key="",
            )

    def test_valid_config_passes(self):
        """No error when all required fields are present."""
        validate_backup_config(
            bucket="my-bucket",
            access_key_id="key",
            secret_access_key="secret",
        )


def _make_subprocess_side_effect():
    """Create a subprocess.run side effect that fakes pg_dump."""
    call_count = 0

    def side_effect(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # pg_dump --version
            result = MagicMock()
            result.stdout = "pg_dump (PostgreSQL) 15.4"
            return result
        else:
            # pg_dump -Fc ... -f <path>
            f_index = cmd.index("-f") + 1
            Path(cmd[f_index]).write_bytes(b"fake dump data")
            result = MagicMock()
            result.returncode = 0
            return result

    return side_effect


def _configure_mock_settings(mock_settings):
    """Apply standard mock settings for backup tests."""
    mock_settings.BACKUP_ENABLED = True
    mock_settings.BACKUP_STORAGE_BUCKET = "test-bucket"
    mock_settings.BACKUP_STORAGE_PREFIX = "backups"
    mock_settings.BACKUP_STORAGE_ENDPOINT_URL = "https://fsn1.your-objectstorage.com"
    mock_settings.BACKUP_STORAGE_REGION = "fsn1"
    mock_settings.BACKUP_STORAGE_ACCESS_KEY_ID = "test-key"
    mock_settings.BACKUP_STORAGE_SECRET_ACCESS_KEY = "test-secret"
    mock_settings.DB_HOST = "db.example.com"
    mock_settings.DB_HOST_DIRECT = None
    mock_settings.DB_PORT = 5432
    mock_settings.DB_NAME = "leadr"
    mock_settings.DB_USER = "leadr"
    mock_settings.DB_PASSWORD = "pass"


class TestUploadToStorage:
    """Tests for the upload_to_storage function."""

    @patch("leadr.common.utils.backup.boto3")
    @patch("leadr.common.utils.backup.settings")
    def test_uploads_both_files(self, mock_settings, mock_boto3, tmp_path):
        """Uploads dump and manifest to the configured bucket."""
        _configure_mock_settings(mock_settings)

        dump_path = tmp_path / "test.dump"
        manifest_path = tmp_path / "test.manifest.json"
        dump_path.write_bytes(b"dump")
        manifest_path.write_text("{}")

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        upload_to_storage(
            dump_path=dump_path,
            manifest_path=manifest_path,
            dump_key="backups/2026/04/leadr.dump",
            manifest_key="backups/2026/04/leadr.manifest.json",
        )

        mock_boto3.client.assert_called_once_with(
            "s3",
            endpoint_url="https://fsn1.your-objectstorage.com",
            region_name="fsn1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
        )
        assert mock_s3.upload_file.call_count == 2


class TestRunBackup:
    """Tests for the main backup flow."""

    @patch("leadr.common.utils.backup.settings")
    def test_backup_disabled_exits_cleanly(self, mock_settings):
        """When BACKUP_ENABLED=False, run_backup returns without error."""
        mock_settings.BACKUP_ENABLED = False

        result = run_backup()

        assert result is None

    @patch("leadr.common.utils.backup.boto3")
    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_backup_flow_uploads_dump_and_manifest(
        self, mock_settings, mock_subprocess, mock_boto3
    ):
        """Full flow: pg_dump runs, dump + manifest uploaded, temp files cleaned."""
        _configure_mock_settings(mock_settings)
        mock_subprocess.run.side_effect = _make_subprocess_side_effect()
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        run_backup()

        # Verify two uploads happened (dump + manifest)
        assert mock_s3_client.upload_file.call_count == 2

        dump_call = mock_s3_client.upload_file.call_args_list[0]
        assert dump_call[1]["Bucket"] == "test-bucket"
        assert dump_call[1]["Key"].startswith("backups/")
        assert dump_call[1]["Key"].endswith(".dump")

        manifest_call = mock_s3_client.upload_file.call_args_list[1]
        assert manifest_call[1]["Bucket"] == "test-bucket"
        assert manifest_call[1]["Key"].endswith(".manifest.json")

    @patch("leadr.common.utils.backup.settings")
    def test_missing_config_raises_when_enabled(self, mock_settings):
        """When enabled but bucket is empty, raises ValueError."""
        mock_settings.BACKUP_ENABLED = True
        mock_settings.BACKUP_STORAGE_BUCKET = ""
        mock_settings.BACKUP_STORAGE_ACCESS_KEY_ID = "key"
        mock_settings.BACKUP_STORAGE_SECRET_ACCESS_KEY = "secret"

        with pytest.raises(ValueError, match="BACKUP_STORAGE_BUCKET"):
            run_backup()

    @patch("leadr.common.utils.backup.boto3")
    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_uses_db_host_direct_when_available(self, mock_settings, mock_subprocess, mock_boto3):
        """When DB_HOST_DIRECT is set, pg_dump uses it instead of DB_HOST."""
        _configure_mock_settings(mock_settings)
        mock_settings.DB_HOST = "pooler.example.com"
        mock_settings.DB_HOST_DIRECT = "direct.example.com"
        mock_subprocess.run.side_effect = _make_subprocess_side_effect()
        mock_boto3.client.return_value = MagicMock()

        run_backup()

        pg_dump_call = mock_subprocess.run.call_args_list[1]
        pg_dump_cmd = pg_dump_call[0][0]
        h_index = pg_dump_cmd.index("-h") + 1
        assert pg_dump_cmd[h_index] == "direct.example.com"

    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_pg_dump_failure_raises(self, mock_settings, mock_subprocess):
        """When pg_dump fails, the script raises an error."""
        _configure_mock_settings(mock_settings)
        mock_settings.DB_HOST_DIRECT = None

        call_count = 0

        def subprocess_side_effect(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.stdout = "pg_dump (PostgreSQL) 15.4"
                return result
            else:
                raise subprocess.CalledProcessError(1, "pg_dump", stderr=b"connection refused")

        mock_subprocess.run.side_effect = subprocess_side_effect
        mock_subprocess.CalledProcessError = subprocess.CalledProcessError

        with pytest.raises(subprocess.CalledProcessError):
            run_backup()

    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_manifest_includes_md5(self, mock_settings, mock_subprocess, tmp_path):
        """Manifest contains a valid MD5 hex digest of the dump file."""
        _configure_mock_settings(mock_settings)
        mock_subprocess.run.side_effect = _make_subprocess_side_effect()

        run_backup(local_dir=tmp_path)

        # Find the manifest file
        manifest_files = list(tmp_path.glob("*.manifest.json"))
        assert len(manifest_files) == 1
        manifest = json.loads(manifest_files[0].read_text())

        assert "backup_md5" in manifest
        assert len(manifest["backup_md5"]) == 32
        assert all(c in "0123456789abcdef" for c in manifest["backup_md5"])

    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_local_mode_stores_files_locally(self, mock_settings, mock_subprocess, tmp_path):
        """With --local, files are stored in the given directory, no upload occurs."""
        _configure_mock_settings(mock_settings)
        mock_subprocess.run.side_effect = _make_subprocess_side_effect()

        local_dir = tmp_path / "my_backups"
        run_backup(local_dir=local_dir)

        # Directory was created
        assert local_dir.exists()

        # Dump and manifest files exist
        dump_files = list(local_dir.glob("*.dump"))
        manifest_files = list(local_dir.glob("*.manifest.json"))
        assert len(dump_files) == 1
        assert len(manifest_files) == 1

    @patch("leadr.common.utils.backup.subprocess")
    @patch("leadr.common.utils.backup.settings")
    def test_local_mode_skips_upload_validation(self, mock_settings, mock_subprocess, tmp_path):
        """With --local, missing storage credentials don't raise errors."""
        mock_settings.BACKUP_ENABLED = True
        mock_settings.BACKUP_STORAGE_BUCKET = ""
        mock_settings.BACKUP_STORAGE_PREFIX = "backups"
        mock_settings.BACKUP_STORAGE_ENDPOINT_URL = None
        mock_settings.BACKUP_STORAGE_REGION = ""
        mock_settings.BACKUP_STORAGE_ACCESS_KEY_ID = ""
        mock_settings.BACKUP_STORAGE_SECRET_ACCESS_KEY = ""
        mock_settings.DB_HOST = "localhost"
        mock_settings.DB_HOST_DIRECT = None
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "leadr"
        mock_settings.DB_USER = "leadr"
        mock_settings.DB_PASSWORD = ""

        mock_subprocess.run.side_effect = _make_subprocess_side_effect()

        # Should not raise despite empty storage config
        run_backup(local_dir=tmp_path)

        dump_files = list(tmp_path.glob("*.dump"))
        assert len(dump_files) == 1
