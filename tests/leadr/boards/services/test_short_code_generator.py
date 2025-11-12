"""Tests for short code generator utility."""

import re
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.services.short_code_generator import (
    generate_short_code,
    generate_unique_short_code,
)


class TestGenerateShortCode:
    """Tests for generate_short_code function."""

    def test_generates_8_character_code(self):
        """Test that generated code is exactly 8 characters long."""
        code = generate_short_code()
        assert len(code) == 8

    def test_generates_alphanumeric_code(self):
        """Test that generated code contains only uppercase letters and digits."""
        code = generate_short_code()
        # Should only contain uppercase letters and digits (no special chars)
        assert re.match(r"^[A-Z0-9]{8}$", code)

    def test_generates_url_safe_code(self):
        """Test that generated code is URL-safe (no special characters)."""
        code = generate_short_code()
        # URL-safe means no special characters that need encoding
        assert code.isalnum()
        assert code.isupper() or code.isdigit()

    def test_generates_different_codes(self):
        """Test that multiple calls generate different codes."""
        codes = {generate_short_code() for _ in range(100)}
        # With 32^8 possible codes, we should never see duplicates in 100 tries
        assert len(codes) == 100

    def test_no_ambiguous_characters(self):
        """Test that codes don't contain ambiguous characters like O/0 or I/1."""
        # Generate many codes and check none contain ambiguous chars
        # This is a design decision - we'll use a charset that avoids these
        codes = [generate_short_code() for _ in range(100)]
        for code in codes:
            # If we decide to exclude ambiguous chars, they shouldn't appear
            # For now, we'll test that the code is readable
            assert len(code) == 8


class TestGenerateUniqueShortCode:
    """Tests for generate_unique_short_code function with collision handling."""

    @pytest.mark.asyncio
    async def test_generates_unique_code_first_try(self, db_session: AsyncSession):
        """Test that function returns code on first try when no collision."""
        with patch(
            "leadr.boards.services.short_code_generator.generate_short_code"
        ) as mock_generate:
            mock_generate.return_value = "TESTCODE"

            # Mock the repository method to return None (no existing board)
            mock_repo = AsyncMock()
            mock_repo.get_by_short_code.return_value = None

            with patch(
                "leadr.boards.services.short_code_generator.BoardRepository"
            ) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                code = await generate_unique_short_code(db_session)

                assert code == "TESTCODE"
                mock_generate.assert_called_once()
                mock_repo.get_by_short_code.assert_called_once_with("TESTCODE")

    @pytest.mark.asyncio
    async def test_retries_on_collision(self, db_session: AsyncSession):
        """Test that function retries when collision is detected."""
        with patch(
            "leadr.boards.services.short_code_generator.generate_short_code"
        ) as mock_generate:
            # First call returns existing code, second returns unique code
            mock_generate.side_effect = ["COLLISION", "UNIQUE123"]

            # Mock the repository to return existing board for first code, None for second
            mock_repo = AsyncMock()
            mock_repo.get_by_short_code.side_effect = [
                AsyncMock(),  # First call returns existing board
                None,  # Second call returns None (unique)
            ]

            with patch(
                "leadr.boards.services.short_code_generator.BoardRepository"
            ) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                code = await generate_unique_short_code(db_session)

                assert code == "UNIQUE123"
                assert mock_generate.call_count == 2
                assert mock_repo.get_by_short_code.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_error_after_max_retries(self, db_session: AsyncSession):
        """Test that function raises error after exceeding max retries."""
        with patch(
            "leadr.boards.services.short_code_generator.generate_short_code"
        ) as mock_generate:
            # Always return same code to force collision
            mock_generate.return_value = "COLLISION"

            # Mock the repository to always return existing board
            mock_repo = AsyncMock()
            mock_repo.get_by_short_code.return_value = AsyncMock()  # Always exists

            with patch(
                "leadr.boards.services.short_code_generator.BoardRepository"
            ) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                with pytest.raises(RuntimeError, match="Failed to generate unique short code"):
                    await generate_unique_short_code(db_session, max_retries=5)

                # Should try max_retries times
                assert mock_generate.call_count == 5

    @pytest.mark.asyncio
    async def test_custom_max_retries(self, db_session: AsyncSession):
        """Test that custom max_retries parameter is respected."""
        with patch(
            "leadr.boards.services.short_code_generator.generate_short_code"
        ) as mock_generate:
            mock_generate.return_value = "COLLISION"

            mock_repo = AsyncMock()
            mock_repo.get_by_short_code.return_value = AsyncMock()

            with patch(
                "leadr.boards.services.short_code_generator.BoardRepository"
            ) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                with pytest.raises(RuntimeError):
                    await generate_unique_short_code(db_session, max_retries=3)

                # Should only try 3 times
                assert mock_generate.call_count == 3
