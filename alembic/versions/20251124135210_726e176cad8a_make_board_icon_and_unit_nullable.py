"""make board icon and unit nullable

Revision ID: 726e176cad8a
Revises: 93ff1903e86b
Create Date: 2025-11-24 13:52:10.416787

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "726e176cad8a"
down_revision: str | Sequence[str] | None = "93ff1903e86b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make icon and unit columns nullable
    op.alter_column("boards", "icon", nullable=True)
    op.alter_column("boards", "unit", nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert icon and unit columns to NOT NULL
    # Note: This requires ensuring all rows have non-null values first
    op.alter_column("boards", "icon", nullable=False)
    op.alter_column("boards", "unit", nullable=False)
