"""Add composite index for score ranking

Revision ID: 554c52ba9114
Revises: 7221441aadab
Create Date: 2026-01-12 16:16:02.760774

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "554c52ba9114"
down_revision: str | Sequence[str] | None = "7221441aadab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create composite index for efficient score ranking queries.
    # This index supports:
    # - Filtering by board_id
    # - Sorting by value (both ASC and DESC - B-tree can traverse both directions)
    # - Tie-breaking by created_at and id
    # - Excluding soft-deleted scores
    op.create_index(
        "ix_scores_ranking",
        "scores",
        ["board_id", "value", "created_at", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_scores_ranking", table_name="scores")
