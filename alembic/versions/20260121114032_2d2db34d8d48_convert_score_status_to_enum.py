"""convert_score_status_to_enum

Revision ID: 2d2db34d8d48
Revises: 542a6a8d3ae5
Create Date: 2026-01-21 11:40:32.392592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2d2db34d8d48'
down_revision: Union[str, Sequence[str], None] = '542a6a8d3ae5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the score_status enum type
    score_status = postgresql.ENUM(
        'provisional', 'active', 'under_review', 'rejected',
        name='score_status',
        create_type=False,
    )
    score_status.create(op.get_bind(), checkfirst=True)

    # Drop the server_default before changing type
    op.alter_column('scores', 'status', server_default=None)

    # Convert the column from String to enum
    op.alter_column(
        'scores',
        'status',
        type_=score_status,
        postgresql_using='status::score_status',
    )

    # Add the new server_default with the enum type
    op.alter_column('scores', 'status', server_default='provisional')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the server_default before changing type
    op.alter_column('scores', 'status', server_default=None)

    # Convert the column back to String
    op.alter_column(
        'scores',
        'status',
        type_=sa.String(),
        postgresql_using='status::text',
    )

    # Add the server_default back as string
    op.alter_column('scores', 'status', server_default='active')

    # Drop the enum type
    postgresql.ENUM(name='score_status').drop(op.get_bind(), checkfirst=True)
