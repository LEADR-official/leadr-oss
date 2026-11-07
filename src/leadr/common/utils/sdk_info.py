"""SDK information parsing from leadr-client header."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SdkInfo:
    """Parsed SDK information from leadr-client header.

    Attributes:
        sdk_type: SDK identifier (e.g., "sdk-godot", "sdk-unity")
        version: SDK version string (e.g., "0.1.2")
        platform: Platform identifier (e.g., "web", "windows", "macos")
    """

    sdk_type: str
    version: str
    platform: str


# Pattern matches: sdk-godot; v=0.1.2; runtime=godot-4.6; platform=web; arch=wasm32
_SDK_PATTERN = re.compile(
    r"^(sdk-[a-zA-Z0-9_-]+);\s*v=([0-9]+\.[0-9]+\.[0-9]+)(?:;.*?platform=([a-zA-Z0-9_-]+))?"
)


def parse_sdk_info(leadr_client: str) -> SdkInfo | None:
    """Parse SDK info from leadr-client header.

    Expected format: sdk-godot; v=0.1.2; runtime=godot-4.6; platform=web; arch=wasm32

    Args:
        leadr_client: Raw leadr-client header string

    Returns:
        SdkInfo if valid LEADR SDK header, None otherwise
    """
    if not leadr_client:
        return None

    match = _SDK_PATTERN.match(leadr_client)
    if not match:
        return None

    return SdkInfo(
        sdk_type=match.group(1),
        version=match.group(2),
        platform=match.group(3) or "unknown",
    )


def version_less_than(version: str, target: str) -> bool:
    """Compare semantic versions.

    Args:
        version: Version to check (e.g., "0.1.2")
        target: Target version to compare against (e.g., "0.1.5")

    Returns:
        True if version < target, False otherwise
    """
    try:
        v_parts = [int(p) for p in version.split(".")]
        t_parts = [int(p) for p in target.split(".")]

        # Pad shorter version with zeros
        while len(v_parts) < len(t_parts):
            v_parts.append(0)
        while len(t_parts) < len(v_parts):
            t_parts.append(0)

        return v_parts < t_parts
    except (ValueError, AttributeError):
        # Invalid version format - assume not less than
        return False
