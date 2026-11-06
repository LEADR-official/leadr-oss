"""SDK information parsing from user-agent headers."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SdkInfo:
    """Parsed SDK information from user-agent header.

    Attributes:
        sdk_type: SDK identifier (e.g., "sdk-godot", "sdk-unity")
        version: SDK version string (e.g., "0.1.2")
        platform: Platform identifier (e.g., "web", "windows", "macos")
    """

    sdk_type: str
    version: str
    platform: str


# Pattern matches: leadr_client=sdk-godot/0.1.2; platform=web; arch=wasm32
_SDK_PATTERN = re.compile(
    r"leadr_client=([a-zA-Z0-9_-]+)/([0-9]+\.[0-9]+\.[0-9]+)"
    r"(?:;?\s*platform=([a-zA-Z0-9_-]+))?"
)


def parse_sdk_info(user_agent: str) -> SdkInfo | None:
    """Parse SDK info from user-agent header.

    Expected format: leadr_client=sdk-godot/0.1.2; platform=web; arch=wasm32

    Args:
        user_agent: Raw user-agent header string

    Returns:
        SdkInfo if valid LEADR SDK user-agent, None otherwise
    """
    if not user_agent:
        return None

    match = _SDK_PATTERN.search(user_agent)
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
