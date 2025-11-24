"""Tests for slug generation utilities."""

import pytest

from leadr.common.utils.slug import generate_slug, generate_unique_slug_with_retry


class TestGenerateSlug:
    """Tests for generate_slug function."""

    def test_basic_slug_generation(self):
        """Test basic conversion to slug format."""
        assert generate_slug("Hello World") == "hello-world"
        assert generate_slug("Speed Run Board") == "speed-run-board"

    def test_multiple_spaces(self):
        """Test that multiple spaces are converted to single hyphen."""
        assert generate_slug("Hello   World") == "hello-world"
        assert generate_slug("Test  Board  Name") == "test-board-name"

    def test_leading_and_trailing_spaces(self):
        """Test that leading/trailing spaces are stripped."""
        assert generate_slug("  Hello World  ") == "hello-world"
        assert generate_slug("Test") == "test"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert generate_slug("Hello@World!") == "helloworld"
        assert generate_slug("Test#Board$Name%") == "testboardname"
        assert generate_slug("Speed-Run") == "speed-run"  # Hyphens preserved
        assert generate_slug("Test_Board") == "test-board"  # Underscores converted to hyphens

    def test_unicode_characters(self):
        """Test handling of unicode/accented characters."""
        # Unicode should be transliterated or removed
        assert generate_slug("Café") == "cafe"
        assert generate_slug("Über Board") == "uber-board"
        assert generate_slug("Niño") == "nino"

    def test_numbers_preserved(self):
        """Test that numbers are preserved in slugs."""
        assert generate_slug("Board 123") == "board-123"
        assert generate_slug("Test 1 2 3") == "test-1-2-3"

    def test_consecutive_hyphens_merged(self):
        """Test that consecutive hyphens are merged to single hyphen."""
        assert generate_slug("Hello---World") == "hello-world"
        assert generate_slug("Test -- Board") == "test-board"

    def test_leading_trailing_hyphens_removed(self):
        """Test that leading/trailing hyphens are removed."""
        assert generate_slug("-Hello-") == "hello"
        assert generate_slug("--Test--") == "test"

    def test_mixed_case_converted_to_lowercase(self):
        """Test that mixed case is converted to lowercase."""
        assert generate_slug("MyBoard") == "myboard"
        assert generate_slug("SpeedRUN") == "speedrun"

    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot generate slug from empty text"):
            generate_slug("")
        with pytest.raises(ValueError, match="Cannot generate slug from empty text"):
            generate_slug("   ")

    def test_only_special_characters(self):
        """Test that string with only special chars raises ValueError."""
        with pytest.raises(
            ValueError, match="Cannot generate slug from text with no valid characters"
        ):
            generate_slug("@#$%")
        with pytest.raises(
            ValueError, match="Cannot generate slug from text with no valid characters"
        ):
            generate_slug("---")

    def test_slug_length_validation(self):
        """Test that generated slug respects length constraints."""
        # Very long input should be truncated
        long_text = "a" * 100
        slug = generate_slug(long_text)
        assert len(slug) <= 50  # Max length should be 50

    def test_real_world_examples(self):
        """Test real-world board name examples."""
        assert generate_slug("Top Scores") == "top-scores"
        assert generate_slug("Daily Challenge") == "daily-challenge"
        assert generate_slug("Speedrun Leaderboard") == "speedrun-leaderboard"
        assert generate_slug("PvP Rankings") == "pvp-rankings"
        assert generate_slug("Season 1 Winners") == "season-1-winners"


class TestGenerateUniqueSlugWithRetry:
    """Tests for generate_unique_slug_with_retry function."""

    @pytest.mark.asyncio
    async def test_no_collision(self):
        """Test that base slug is returned when no collision exists."""

        async def check_exists(slug: str) -> bool:
            return False

        result = await generate_unique_slug_with_retry("Test Board", check_exists)
        assert result == "test-board"

    @pytest.mark.asyncio
    async def test_single_collision(self):
        """Test that numeric suffix is added on first collision."""

        async def check_exists(slug: str) -> bool:
            return slug == "test-board"

        result = await generate_unique_slug_with_retry("Test Board", check_exists)
        assert result == "test-board-2"

    @pytest.mark.asyncio
    async def test_multiple_collisions(self):
        """Test that suffix increments until unique slug is found."""

        async def check_exists(slug: str) -> bool:
            return slug in ["test-board", "test-board-2", "test-board-3"]

        result = await generate_unique_slug_with_retry("Test Board", check_exists)
        assert result == "test-board-4"

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that ValueError is raised when max retries exceeded."""

        async def check_exists(slug: str) -> bool:
            return True  # All slugs already exist

        with pytest.raises(ValueError, match="Unable to generate unique slug after 3 retries"):
            await generate_unique_slug_with_retry("Test Board", check_exists, max_retries=3)

    @pytest.mark.asyncio
    async def test_respects_max_length(self):
        """Test that generated slugs respect max_length constraint."""
        long_text = "a" * 50  # 50 character base slug

        async def check_exists(slug: str) -> bool:
            return slug == "a" * 50

        result = await generate_unique_slug_with_retry(long_text, check_exists, max_length=50)
        # Should be truncated to fit suffix
        assert len(result) <= 50
        assert result.endswith("-2")

    @pytest.mark.asyncio
    async def test_invalid_base_text(self):
        """Test that ValueError is raised for invalid base text."""

        async def check_exists(slug: str) -> bool:
            return False

        with pytest.raises(ValueError, match="Cannot generate slug from empty text"):
            await generate_unique_slug_with_retry("", check_exists)

    @pytest.mark.asyncio
    async def test_collision_check_called_correctly(self):
        """Test that collision check function is called with correct slugs."""
        checked_slugs = []

        async def check_exists(slug: str) -> bool:
            checked_slugs.append(slug)
            return slug in ["my-board", "my-board-2"]

        result = await generate_unique_slug_with_retry("My Board", check_exists)

        assert result == "my-board-3"
        assert checked_slugs == ["my-board", "my-board-2", "my-board-3"]
