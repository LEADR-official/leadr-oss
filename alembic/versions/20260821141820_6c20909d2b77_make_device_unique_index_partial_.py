"""make device unique index partial exclude deleted

Revision ID: 6c20909d2b77
Revises: c3f30ab1f058
Create Date: 2026-08-21 14:18:20.996197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c20909d2b77'
down_revision: Union[str, Sequence[str], None] = 'c3f30ab1f058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old non-partial unique index
    op.drop_index("ix_devices_game_device", table_name="devices")

    # Create partial unique index excluding soft-deleted records
    op.create_index(
        "ix_devices_game_device",
        "devices",
        ["game_id", "client_fingerprint"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop partial unique index
    op.drop_index("ix_devices_game_device", table_name="devices")

    # Recreate original non-partial unique index
    op.create_index(
        "ix_devices_game_device",
        "devices",
        ["game_id", "client_fingerprint"],
        unique=True,
    )
