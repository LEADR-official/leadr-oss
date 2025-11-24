"""add slug to games with global unique constraint

Revision ID: 47e86f46d73f
Revises: e76dbceb748c
Create Date: 2025-11-24 12:14:57.711972

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47e86f46d73f"
down_revision: str | Sequence[str] | None = "e76dbceb748c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add slug column to games table with a temporary nullable state
    op.add_column("games", sa.Column("slug", sa.String(), nullable=True))

    # Set slug values for existing games (generate from name)
    # This uses a simple transformation: lowercase + replace spaces with hyphens
    op.execute("""
        UPDATE games
        SET slug = LOWER(REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(TRIM(name), '[^a-zA-Z0-9\\s-]', '', 'g'),
                '\\s+', '-', 'g'
            ),
            '^-+|-+$', '', 'g'
        ))
    """)

    # Make slug non-nullable now that all rows have values
    op.alter_column("games", "slug", nullable=False)

    # Create unique constraint and index for slug (globally unique)
    op.create_unique_constraint("uq_game_slug", "games", ["slug"])
    op.create_index(op.f("ix_games_slug"), "games", ["slug"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and constraint
    op.drop_index(op.f("ix_games_slug"), table_name="games")
    op.drop_constraint("uq_game_slug", "games", type_="unique")

    # Drop slug column
    op.drop_column("games", "slug")
