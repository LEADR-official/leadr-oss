"""rename user_id to device_id in score_submission_metadata

Revision ID: f7c5f54c8e30
Revises: 12b367f5d9da
Create Date: 2025-11-12 15:08:29.961291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c5f54c8e30'
down_revision: Union[str, Sequence[str], None] = '12b367f5d9da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename user_id column to device_id in score_submission_metadata table
    op.alter_column(
        'score_submission_metadata',
        'user_id',
        new_column_name='device_id',
        existing_type=sa.UUID(),
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Rename device_id column back to user_id
    op.alter_column(
        'score_submission_metadata',
        'device_id',
        new_column_name='user_id',
        existing_type=sa.UUID(),
        existing_nullable=False
    )
