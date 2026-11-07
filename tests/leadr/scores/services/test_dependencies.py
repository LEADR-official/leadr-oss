"""Tests for score service dependencies."""

from unittest.mock import MagicMock

from leadr.scores.services.dependencies import has_fingerprint_collision_bug


class TestHasFingerprintCollisionBug:
    """Tests for has_fingerprint_collision_bug dependency."""

    def test_godot_sdk_below_fix_version_detected(self):
        """Test that Godot SDK <0.2.0 on web is detected."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.1.2; runtime=godot-4.6; platform=web; arch=wasm32"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is True

    def test_new_godot_web_not_detected(self):
        """Test that new Godot web SDK is not flagged."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.2.0; runtime=godot-4.6; platform=web; arch=wasm32"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_godot_desktop_not_detected(self):
        """Test that Godot desktop builds are not flagged (no fingerprint bug)."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.1.2; runtime=godot-4.6; platform=windows; arch=x86_64"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_godot_macos_not_detected(self):
        """Test that Godot macOS builds are not flagged."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.1.2; runtime=godot-4.4; platform=macos; arch=arm64"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_unity_sdk_not_detected(self):
        """Test that Unity SDK is not flagged."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-unity; v=0.1.0; runtime=unity-2023; platform=web; arch=wasm32"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_non_leadr_header_not_detected(self):
        """Test that non-LEADR header returns False."""
        request = MagicMock()
        request.headers.get.return_value = "Mozilla/5.0"

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_empty_header_not_detected(self):
        """Test that empty header returns False."""
        request = MagicMock()
        request.headers.get.return_value = ""

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_missing_header_not_detected(self):
        """Test that missing header returns False."""
        request = MagicMock()
        request.headers.get.return_value = ""

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_exact_fix_version_not_detected(self):
        """Test that exact fix version (0.2.0) is not flagged."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.2.0; runtime=godot-4.6; platform=web; arch=wasm32"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is False

    def test_version_just_below_fix_detected(self):
        """Test that version just below fix (0.1.9) is flagged."""
        request = MagicMock()
        request.headers.get.return_value = (
            "sdk-godot; v=0.1.9; runtime=godot-4.6; platform=web; arch=wasm32"
        )

        result = has_fingerprint_collision_bug(request)

        assert result is True
