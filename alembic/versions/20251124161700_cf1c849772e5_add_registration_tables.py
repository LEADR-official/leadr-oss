"""add_registration_tables

Revision ID: cf1c849772e5
Revises: 726e176cad8a
Create Date: 2025-11-24 16:17:00.496530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf1c849772e5'
down_revision: Union[str, Sequence[str], None] = '726e176cad8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create verification_codes table
    op.create_table(
        "verification_codes",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "used", "expired", name="verification_code_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_verification_codes_email"), "verification_codes", ["email"], unique=False)
    op.create_index(
        op.f("ix_verification_codes_expires_at"), "verification_codes", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_verification_codes_email_status", "verification_codes", ["email", "status"], unique=False
    )

    # Create jam_codes table
    op.create_table(
        "jam_codes",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("features", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("current_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jam_codes_code"), "jam_codes", ["code"], unique=True)
    op.create_index("ix_jam_codes_active_expires", "jam_codes", ["active", "expires_at"], unique=False)

    # Create jam_code_redemptions table
    op.create_table(
        "jam_code_redemptions",
        sa.Column("jam_code_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["jam_code_id"], ["jam_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_jam_code_redemptions_jam_code_id"), "jam_code_redemptions", ["jam_code_id"], unique=False
    )
    op.create_index(
        op.f("ix_jam_code_redemptions_account_id"), "jam_code_redemptions", ["account_id"], unique=False
    )
    op.create_index(
        "ix_jam_code_redemptions_jam_code_account",
        "jam_code_redemptions",
        ["jam_code_id", "account_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (children first)
    op.drop_index("ix_jam_code_redemptions_jam_code_account", table_name="jam_code_redemptions")
    op.drop_index(op.f("ix_jam_code_redemptions_account_id"), table_name="jam_code_redemptions")
    op.drop_index(op.f("ix_jam_code_redemptions_jam_code_id"), table_name="jam_code_redemptions")
    op.drop_table("jam_code_redemptions")

    op.drop_index("ix_jam_codes_active_expires", table_name="jam_codes")
    op.drop_index(op.f("ix_jam_codes_code"), table_name="jam_codes")
    op.drop_table("jam_codes")

    op.drop_index("ix_verification_codes_email_status", table_name="verification_codes")
    op.drop_index(op.f("ix_verification_codes_expires_at"), table_name="verification_codes")
    op.drop_index(op.f("ix_verification_codes_email"), table_name="verification_codes")
    op.drop_table("verification_codes")

    # Drop enums
    op.execute("DROP TYPE verification_code_status;")
