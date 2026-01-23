"""migrate nonces from device_id to identity_id

Revision ID: 87e926a5a3a9
Revises: 1b9ec17c7718
Create Date: 2026-01-23 19:48:57.526656

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "87e926a5a3a9"
down_revision: Union[str, Sequence[str], None] = "1b9ec17c7718"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: migrate nonces from device_id to identity_id.

    Since nonces are short-lived (60 second TTL), we delete all existing rows
    rather than backfilling. New nonces will be created with identity_id.
    """
    # Delete all existing nonces (they expire quickly anyway)
    op.execute("DELETE FROM nonces")

    # Drop the old foreign key and index
    op.drop_constraint(op.f("nonces_device_id_fkey"), "nonces", type_="foreignkey")
    op.drop_index(op.f("ix_nonces_device_id"), table_name="nonces")

    # Drop the old column
    op.drop_column("nonces", "device_id")

    # Add the new column with foreign key to identities
    op.add_column("nonces", sa.Column("identity_id", sa.Uuid(), nullable=False))
    op.create_index(op.f("ix_nonces_identity_id"), "nonces", ["identity_id"], unique=False)
    op.create_foreign_key(
        op.f("nonces_identity_id_fkey"),
        "nonces",
        "identities",
        ["identity_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema: revert nonces from identity_id to device_id."""
    # Delete all existing nonces
    op.execute("DELETE FROM nonces")

    # Drop the new foreign key and index
    op.drop_constraint(op.f("nonces_identity_id_fkey"), "nonces", type_="foreignkey")
    op.drop_index(op.f("ix_nonces_identity_id"), table_name="nonces")

    # Drop the new column
    op.drop_column("nonces", "identity_id")

    # Add the old column with foreign key to devices
    op.add_column("nonces", sa.Column("device_id", sa.Uuid(), nullable=False))
    op.create_index(op.f("ix_nonces_device_id"), "nonces", ["device_id"], unique=False)
    op.create_foreign_key(
        op.f("nonces_device_id_fkey"),
        "nonces",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )
