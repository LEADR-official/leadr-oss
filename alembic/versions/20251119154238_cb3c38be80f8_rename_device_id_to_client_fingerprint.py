"""rename device_id to client_fingerprint

Revision ID: cb3c38be80f8
Revises: 420fd101ae71
Create Date: 2025-11-19 15:42:38.607340

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb3c38be80f8"
down_revision: str | Sequence[str] | None = "420fd101ae71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column instead of drop+add to preserve data
    op.alter_column(
        "devices", "device_id", new_column_name="client_fingerprint", type_=sa.String(length=64)
    )

    # Recreate unique index with new column name
    op.drop_index("ix_devices_game_device", table_name="devices")
    op.create_index(
        "ix_devices_game_device", "devices", ["game_id", "client_fingerprint"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse: rename back to device_id
    op.drop_index("ix_devices_game_device", table_name="devices")
    op.create_index("ix_devices_game_device", "devices", ["game_id", "device_id"], unique=True)

    op.alter_column(
        "devices", "client_fingerprint", new_column_name="device_id", type_=sa.VARCHAR()
    )
