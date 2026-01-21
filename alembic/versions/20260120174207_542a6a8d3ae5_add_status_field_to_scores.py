"""Add status field to scores

Revision ID: 542a6a8d3ae5
Revises: d25522b75751
Create Date: 2026-01-20 17:42:07.971478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '542a6a8d3ae5'
down_revision: Union[str, Sequence[str], None] = 'd25522b75751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'scores',
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
    )
    op.create_index(op.f('ix_scores_status'), 'scores', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_scores_status'), table_name='scores')
    op.drop_column('scores', 'status')
