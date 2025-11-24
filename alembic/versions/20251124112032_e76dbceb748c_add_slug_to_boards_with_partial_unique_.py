"""add slug to boards with partial unique constraint

Revision ID: e76dbceb748c
Revises: cb3c38be80f8
Create Date: 2025-11-24 11:20:32.110142

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e76dbceb748c"
down_revision: str | Sequence[str] | None = "cb3c38be80f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add slug column to boards table with a temporary nullable state
    op.add_column("boards", sa.Column("slug", sa.String(), nullable=True))

    # Set slug values for existing boards (generate from name)
    # This uses a simple transformation: lowercase + replace spaces with hyphens
    op.execute("""
        UPDATE boards
        SET slug = LOWER(REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(TRIM(name), '[^a-zA-Z0-9\\s-]', '', 'g'),
                '\\s+', '-', 'g'
            ),
            '^-+|-+$', '', 'g'
        ))
    """)

    # Make slug non-nullable now that all rows have values
    op.alter_column("boards", "slug", nullable=False)

    # Create indexes
    op.create_index(
        "ix_board_slug_unique_when_active",
        "boards",
        ["account_id", "game_id", "slug"],
        unique=True,
        postgresql_where="is_active = true",
    )
    op.create_index(op.f("ix_boards_slug"), "boards", ["slug"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f("ix_boards_slug"), table_name="boards")
    op.drop_index(
        "ix_board_slug_unique_when_active", table_name="boards", postgresql_where="is_active = true"
    )

    # Drop slug column
    op.drop_column("boards", "slug")
