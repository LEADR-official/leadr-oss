#!/usr/bin/env python3
"""Script to fix registration service tests.

Removes @patch decorators and uses direct settings import.
"""

import re
from pathlib import Path


def fix_test_file(file_path: Path) -> None:
    """Fix a single test file by removing settings patches and using direct settings import."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    content = file_path.read_text()
    original_content = content

    # Pattern 1: Add settings import if not present and Mock is being used
    if "from leadr.config import settings" not in content and "@patch" in content:
        # Find the import section and add settings import
        import_match = re.search(r"(from leadr\.\w+.*\n)+", content)
        if import_match:
            last_import_pos = import_match.end()
            content = (
                content[:last_import_pos]
                + "from leadr.config import settings\n"
                + content[last_import_pos:]
            )
        else:
            # If no leadr imports, add after unittest.mock import
            content = re.sub(
                r"(from unittest\.mock import.*\n)",
                r"\1from leadr.config import settings\n",
                content,
                count=1,
            )

    # Pattern 2: Remove @patch decorator lines for settings in services
    content = re.sub(r'    @patch\("leadr\.registration\.services\.\w+\.settings"\)\n', "", content)

    # Pattern 3: Remove @patch decorator lines for settings in routes
    content = re.sub(r'    @patch\("leadr\.registration\.api\.routes\.settings"\)\n', "", content)

    # Pattern 4: Remove mock_settings parameter from function signatures
    # Handles: async def test_something(self, mock_settings, db_session: AsyncSession):
    content = re.sub(r"(async def test_\w+\(self), mock_settings,", r"\1,", content)

    # Pattern 5: Replace all mock_settings usage with settings in function bodies
    content = re.sub(r"\bmock_settings\b", "settings", content)

    # Pattern 6: Fix imports - add AsyncMock if Mock is used
    if "from unittest.mock import Mock" in content and "AsyncMock" not in content:
        content = content.replace(
            "from unittest.mock import Mock", "from unittest.mock import AsyncMock, Mock"
        )

    # Pattern 7: Replace Mock() with AsyncMock() for email service
    content = re.sub(r"mock_email_service = Mock\(\)", "mock_email_service = AsyncMock()", content)

    # Pattern 8: Make mocked email service methods async
    content = re.sub(
        r"mock_email_service\.(\w+) = Mock\(\)", r"mock_email_service.\1 = AsyncMock()", content
    )

    # Pattern 9: Update service instantiation to remove settings parameter
    # VerificationService(db_session, settings, mock_email_service) ->
    # VerificationService(db_session, mock_email_service)
    content = re.sub(
        r"VerificationService\(([^,]+), settings, ([^)]+)\)",
        r"VerificationService(\1, \2)",
        content,
    )

    # Pattern 10: Update RegistrationService instantiation to remove settings parameter
    content = re.sub(
        r"RegistrationService\(\s*([^,]+),\s*settings,\s*", r"RegistrationService(\1, ", content
    )

    if content != original_content:
        file_path.write_text(content)
        print(f"✓ Fixed: {file_path}")
        # Count changes
        removed_patches = original_content.count('@patch("leadr.registration.') - content.count(
            '@patch("leadr.registration.'
        )
        if removed_patches > 0:
            print(f"  - Removed {removed_patches} @patch decorators")
        if (
            "from leadr.config import settings" in content
            and "from leadr.config import settings" not in original_content
        ):
            print("  - Added settings import")
    else:
        print(f"  No changes needed: {file_path}")


def main():
    """Fix all registration service test files."""
    test_files = [
        Path("tests/leadr/registration/services/test_verification_service.py"),
        Path("tests/leadr/registration/services/test_jam_code_service.py"),
        Path("tests/leadr/registration/services/test_registration_service.py"),
        Path("tests/leadr/registration/services/test_repositories.py"),
        Path("tests/leadr/registration/api/test_routes.py"),
    ]

    print("Fixing registration service tests...")
    print("=" * 60)

    for test_file in test_files:
        fix_test_file(test_file)

    print("=" * 60)
    print("All fixes applied!")


if __name__ == "__main__":
    main()
