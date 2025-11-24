"""add_emails_table

Revision ID: 441a8891a99b
Revises: cf1c849772e5
Create Date: 2025-11-24 17:21:35.561891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441a8891a99b'
down_revision: Union[str, Sequence[str], None] = 'cf1c849772e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_priority enum
    op.execute(
        "CREATE TYPE email_priority AS ENUM ('low', 'normal', 'high', 'urgent')"
    )

    # Create email_status enum
    op.execute(
        "CREATE TYPE email_status AS ENUM ('pending', 'sent', 'delivered', 'failed')"
    )

    # Create emails table
    op.create_table(
        "emails",
        sa.Column("to", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("from_email", sa.String(), nullable=True),
        sa.Column("reply_to", sa.String(), nullable=True),
        sa.Column("cc", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("bcc", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "priority",
            sa.Enum("low", "normal", "high", "urgent", name="email_priority"),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "delivered", "failed", name="email_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("template_data", sa.JSON(), nullable=True),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("provider_response", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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

    # Create indexes
    op.create_index(op.f("ix_emails_to"), "emails", ["to"], unique=False)
    op.create_index(op.f("ix_emails_status"), "emails", ["status"], unique=False)
    op.create_index(
        op.f("ix_emails_provider_message_id"), "emails", ["provider_message_id"], unique=False
    )
    op.create_index(op.f("ix_emails_created_at"), "emails", ["created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f("ix_emails_created_at"), table_name="emails")
    op.drop_index(op.f("ix_emails_provider_message_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_status"), table_name="emails")
    op.drop_index(op.f("ix_emails_to"), table_name="emails")

    # Drop table
    op.drop_table("emails")

    # Drop enums
    op.execute("DROP TYPE email_status")
    op.execute("DROP TYPE email_priority")
