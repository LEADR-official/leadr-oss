"""add counter to board_templates and rename template_id to created_from_template_id in boards

Revision ID: 34f35b25fd4f
Revises: 32e23fb2cb23
Create Date: 2025-11-17 16:04:39.222453

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "34f35b25fd4f"
down_revision: str | Sequence[str] | None = "32e23fb2cb23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add counter column to board_templates
    op.add_column("board_templates", sa.Column("counter", sa.String(), nullable=True))

    # Rename template_id to created_from_template_id in boards
    op.alter_column("boards", "template_id", new_column_name="created_from_template_id")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename created_from_template_id back to template_id in boards
    op.alter_column("boards", "created_from_template_id", new_column_name="template_id")

    # Drop counter column from board_templates
    op.drop_column("board_templates", "counter")
