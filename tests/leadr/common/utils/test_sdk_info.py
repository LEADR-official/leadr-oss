"""Tests for SDK info parsing utilities."""

import pytest

from leadr.common.utils.sdk_info import SdkInfo, parse_sdk_info, version_less_than


class TestParseSdkInfo:
    """Tests for parse_sdk_info function."""

    def test_parse_godot_web_header(self):
        """Test parsing Godot SDK web leadr-client header."""
        header = "sdk-godot; v=0.1.2; runtime=godot-4.6; platform=web; arch=wasm32"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "web"

    def test_parse_godot_macos_header(self):
        """Test parsing Godot SDK macOS leadr-client header."""
        header = "sdk-godot; v=0.2.0; runtime=godot-4.4; platform=macos; arch=arm64"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.2.0"
        assert result.platform == "macos"

    def test_parse_godot_windows_header(self):
        """Test parsing Godot SDK Windows leadr-client header."""
        header = "sdk-godot; v=0.1.4; runtime=godot-4.6; platform=windows; arch=x86_64"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.4"
        assert result.platform == "windows"

    def test_parse_unity_header(self):
        """Test parsing Unity SDK leadr-client header."""
        header = "sdk-unity; v=1.0.0; runtime=unity-2023; platform=android; arch=arm64"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-unity"
        assert result.version == "1.0.0"
        assert result.platform == "android"

    def test_parse_without_platform(self):
        """Test parsing header without platform."""
        header = "sdk-godot; v=0.1.2; runtime=godot-4.6"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "unknown"

    def test_parse_minimal_header(self):
        """Test parsing minimal header with just type and version."""
        header = "sdk-godot; v=0.1.2"
        result = parse_sdk_info(header)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "unknown"

    def test_parse_empty_string(self):
        """Test parsing empty header."""
        result = parse_sdk_info("")
        assert result is None

    def test_parse_non_leadr_header(self):
        """Test parsing non-LEADR header."""
        header = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        result = parse_sdk_info(header)
        assert result is None

    def test_parse_malformed_header_missing_version(self):
        """Test parsing malformed header without version."""
        header = "sdk-godot; platform=web"
        result = parse_sdk_info(header)
        assert result is None

    def test_parse_malformed_header_wrong_prefix(self):
        """Test parsing header without sdk- prefix."""
        header = "godot; v=0.1.2; platform=web"
        result = parse_sdk_info(header)
        assert result is None

    def test_sdk_info_immutable(self):
        """Test that SdkInfo is immutable (frozen dataclass)."""
        info = SdkInfo(sdk_type="sdk-godot", version="0.1.2", platform="web")

        with pytest.raises(AttributeError):
            info.version = "0.2.0"  # type: ignore[misc]


class TestVersionLessThan:
    """Tests for version_less_than function."""

    def test_lower_version(self):
        """Test that lower version returns True."""
        assert version_less_than("0.1.2", "0.1.5") is True
        assert version_less_than("0.0.9", "1.0.0") is True
        assert version_less_than("1.0.0", "1.0.1") is True

    def test_equal_version(self):
        """Test that equal version returns False."""
        assert version_less_than("0.1.5", "0.1.5") is False
        assert version_less_than("1.0.0", "1.0.0") is False

    def test_higher_version(self):
        """Test that higher version returns False."""
        assert version_less_than("0.2.0", "0.1.5") is False
        assert version_less_than("1.0.0", "0.9.9") is False
        assert version_less_than("2.0.0", "1.9.9") is False

    def test_version_with_different_lengths(self):
        """Test versions with different segment counts."""
        # 0.1 is treated as 0.1.0
        assert version_less_than("0.1", "0.1.1") is True
        assert version_less_than("0.1.0", "0.1") is False

    def test_invalid_version_format(self):
        """Test invalid version format returns False."""
        assert version_less_than("invalid", "0.1.5") is False
        assert version_less_than("0.1.5", "invalid") is False
        assert version_less_than("", "0.1.5") is False

    def test_major_minor_patch_comparison(self):
        """Test comparison across major, minor, patch versions."""
        # Major version comparison
        assert version_less_than("0.9.9", "1.0.0") is True
        assert version_less_than("1.0.0", "0.9.9") is False

        # Minor version comparison
        assert version_less_than("1.0.9", "1.1.0") is True
        assert version_less_than("1.1.0", "1.0.9") is False

        # Patch version comparison
        assert version_less_than("1.1.0", "1.1.1") is True
        assert version_less_than("1.1.1", "1.1.0") is False
