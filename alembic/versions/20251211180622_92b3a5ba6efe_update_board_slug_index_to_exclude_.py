"""update board slug index to exclude deleted boards

Revision ID: 92b3a5ba6efe
Revises: 9e2b9374eb68
Create Date: 2025-12-11 18:06:22.017105

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "92b3a5ba6efe"
down_revision: str | Sequence[str] | None = "9e2b9374eb68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old partial unique index
    op.drop_index(
        "ix_board_slug_unique_when_active",
        table_name="boards",
        postgresql_where="is_active = true",
    )

    # Create new partial unique index that also excludes deleted boards
    op.create_index(
        "ix_board_slug_unique_when_active",
        "boards",
        ["account_id", "game_id", "slug"],
        unique=True,
        postgresql_where="is_active = true AND deleted_at IS NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new index
    op.drop_index(
        "ix_board_slug_unique_when_active",
        table_name="boards",
        postgresql_where="is_active = true AND deleted_at IS NULL",
    )

    # Recreate the old index
    op.create_index(
        "ix_board_slug_unique_when_active",
        "boards",
        ["account_id", "game_id", "slug"],
        unique=True,
        postgresql_where="is_active = true",
    )
