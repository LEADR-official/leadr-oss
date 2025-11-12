"""rename scores user_id to device_id

Revision ID: 04a38265d653
Revises: 73540480ef92
Create Date: 2025-11-12 16:43:35.425020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04a38265d653'
down_revision: Union[str, Sequence[str], None] = '73540480ef92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old index on user_id
    op.drop_index('ix_scores_user_id', table_name='scores')

    # Rename the column from user_id to device_id
    op.alter_column('scores', 'user_id', new_column_name='device_id')

    # Create new index on device_id
    op.create_index('ix_scores_device_id', 'scores', ['device_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new index on device_id
    op.drop_index('ix_scores_device_id', table_name='scores')

    # Rename the column back from device_id to user_id
    op.alter_column('scores', 'device_id', new_column_name='user_id')

    # Recreate the old index on user_id
    op.create_index('ix_scores_user_id', 'scores', ['user_id'], unique=False)
