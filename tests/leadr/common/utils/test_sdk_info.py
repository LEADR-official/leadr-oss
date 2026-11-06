"""Tests for SDK info parsing utilities."""

import pytest

from leadr.common.utils.sdk_info import SdkInfo, parse_sdk_info, version_less_than


class TestParseSdkInfo:
    """Tests for parse_sdk_info function."""

    def test_parse_godot_web_user_agent(self):
        """Test parsing Godot SDK web user-agent."""
        user_agent = "leadr_client=sdk-godot/0.1.2; platform=web; arch=wasm32"
        result = parse_sdk_info(user_agent)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "web"

    def test_parse_godot_windows_user_agent(self):
        """Test parsing Godot SDK Windows user-agent."""
        user_agent = "leadr_client=sdk-godot/0.1.4; platform=windows; arch=x86_64"
        result = parse_sdk_info(user_agent)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.4"
        assert result.platform == "windows"

    def test_parse_unity_user_agent(self):
        """Test parsing Unity SDK user-agent."""
        user_agent = "leadr_client=sdk-unity/1.0.0; platform=android"
        result = parse_sdk_info(user_agent)

        assert result is not None
        assert result.sdk_type == "sdk-unity"
        assert result.version == "1.0.0"
        assert result.platform == "android"

    def test_parse_without_platform(self):
        """Test parsing user-agent without platform."""
        user_agent = "leadr_client=sdk-godot/0.1.2"
        result = parse_sdk_info(user_agent)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "unknown"

    def test_parse_with_extra_info(self):
        """Test parsing user-agent with additional info."""
        user_agent = "Mozilla/5.0 leadr_client=sdk-godot/0.1.2; platform=web; extra=stuff"
        result = parse_sdk_info(user_agent)

        assert result is not None
        assert result.sdk_type == "sdk-godot"
        assert result.version == "0.1.2"
        assert result.platform == "web"

    def test_parse_empty_string(self):
        """Test parsing empty user-agent."""
        result = parse_sdk_info("")
        assert result is None

    def test_parse_non_leadr_user_agent(self):
        """Test parsing non-LEADR user-agent."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        result = parse_sdk_info(user_agent)
        assert result is None

    def test_parse_malformed_leadr_user_agent(self):
        """Test parsing malformed LEADR user-agent."""
        user_agent = "leadr_client=sdk-godot"  # Missing version
        result = parse_sdk_info(user_agent)
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
