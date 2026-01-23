"""refactor anti-cheat tables to use score_event_id and identity_id

Revision ID: d551a65871fd
Revises: 87e926a5a3a9
Create Date: 2026-01-23 20:24:27.029099

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d551a65871fd"
down_revision: Union[str, Sequence[str], None] = "87e926a5a3a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: refactor anti-cheat tables to use score_event_id and identity_id.

    Since these are anti-cheat metadata tables that can be regenerated from future
    score submissions, we delete all existing rows rather than backfilling.
    """
    # Delete all existing data (anti-cheat metadata regenerates on new submissions)
    op.execute("DELETE FROM score_flags")
    op.execute("DELETE FROM score_submission_metadata")

    # score_flags: score_id → score_event_id
    op.drop_constraint(op.f("score_flags_score_id_fkey"), "score_flags", type_="foreignkey")
    op.drop_index(op.f("ix_score_flags_score_id"), table_name="score_flags")
    op.drop_column("score_flags", "score_id")
    op.add_column("score_flags", sa.Column("score_event_id", sa.Uuid(), nullable=False))
    op.create_index(
        op.f("ix_score_flags_score_event_id"), "score_flags", ["score_event_id"], unique=False
    )
    op.create_foreign_key(
        op.f("score_flags_score_event_id_fkey"),
        "score_flags",
        "score_events",
        ["score_event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # score_submission_metadata: score_id, device_id → score_event_id, identity_id, board_id FK
    op.drop_constraint(
        op.f("score_submission_metadata_score_id_fkey"),
        "score_submission_metadata",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_score_submission_metadata_score_id"), table_name="score_submission_metadata")
    op.drop_index(
        op.f("ix_score_submission_metadata_device_id"), table_name="score_submission_metadata"
    )
    op.drop_column("score_submission_metadata", "score_id")
    op.drop_column("score_submission_metadata", "device_id")

    op.add_column(
        "score_submission_metadata", sa.Column("score_event_id", sa.Uuid(), nullable=False)
    )
    op.add_column("score_submission_metadata", sa.Column("identity_id", sa.Uuid(), nullable=False))

    op.create_index(
        op.f("ix_score_submission_metadata_score_event_id"),
        "score_submission_metadata",
        ["score_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_score_submission_metadata_identity_id"),
        "score_submission_metadata",
        ["identity_id"],
        unique=False,
    )
    op.create_index(
        "ix_score_submission_meta_identity_board",
        "score_submission_metadata",
        ["identity_id", "board_id"],
        unique=True,
    )

    op.create_foreign_key(
        op.f("score_submission_metadata_score_event_id_fkey"),
        "score_submission_metadata",
        "score_events",
        ["score_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("score_submission_metadata_identity_id_fkey"),
        "score_submission_metadata",
        "identities",
        ["identity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("score_submission_metadata_board_id_fkey"),
        "score_submission_metadata",
        "boards",
        ["board_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema: revert anti-cheat tables to score_id and device_id."""
    # Delete all existing data
    op.execute("DELETE FROM score_flags")
    op.execute("DELETE FROM score_submission_metadata")

    # Revert score_submission_metadata: score_event_id, identity_id → score_id, device_id
    op.drop_constraint(
        op.f("score_submission_metadata_board_id_fkey"),
        "score_submission_metadata",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("score_submission_metadata_identity_id_fkey"),
        "score_submission_metadata",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("score_submission_metadata_score_event_id_fkey"),
        "score_submission_metadata",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_score_submission_meta_identity_board", table_name="score_submission_metadata"
    )
    op.drop_index(
        op.f("ix_score_submission_metadata_identity_id"), table_name="score_submission_metadata"
    )
    op.drop_index(
        op.f("ix_score_submission_metadata_score_event_id"), table_name="score_submission_metadata"
    )
    op.drop_column("score_submission_metadata", "identity_id")
    op.drop_column("score_submission_metadata", "score_event_id")

    op.add_column(
        "score_submission_metadata", sa.Column("device_id", sa.UUID(), nullable=False)
    )
    op.add_column(
        "score_submission_metadata", sa.Column("score_id", sa.UUID(), nullable=False)
    )
    op.create_index(
        op.f("ix_score_submission_metadata_device_id"),
        "score_submission_metadata",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_score_submission_metadata_score_id"),
        "score_submission_metadata",
        ["score_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("score_submission_metadata_score_id_fkey"),
        "score_submission_metadata",
        "scores",
        ["score_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Revert score_flags: score_event_id → score_id
    op.drop_constraint(
        op.f("score_flags_score_event_id_fkey"), "score_flags", type_="foreignkey"
    )
    op.drop_index(op.f("ix_score_flags_score_event_id"), table_name="score_flags")
    op.drop_column("score_flags", "score_event_id")
    op.add_column("score_flags", sa.Column("score_id", sa.UUID(), nullable=False))
    op.create_index(op.f("ix_score_flags_score_id"), "score_flags", ["score_id"], unique=False)
    op.create_foreign_key(
        op.f("score_flags_score_id_fkey"),
        "score_flags",
        "scores",
        ["score_id"],
        ["id"],
        ondelete="CASCADE",
    )
