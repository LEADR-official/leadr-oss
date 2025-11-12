"""empty message

Revision ID: 9296c489fd00
Revises: b4d77c391fd8, 04a38265d653
Create Date: 2025-11-12 17:54:16.170193

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "9296c489fd00"
down_revision: str | Sequence[str] | None = ("b4d77c391fd8", "04a38265d653")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
