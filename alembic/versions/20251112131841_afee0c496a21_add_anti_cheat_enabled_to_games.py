"""add_anti_cheat_enabled_to_games

Revision ID: afee0c496a21
Revises: bc1ad0d69fd6
Create Date: 2025-11-12 13:18:41.429925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afee0c496a21'
down_revision: Union[str, Sequence[str], None] = 'bc1ad0d69fd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add anti_cheat_enabled column to games table with default value of True
    op.add_column(
        'games',
        sa.Column('anti_cheat_enabled', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove anti_cheat_enabled column from games table
    op.drop_column('games', 'anti_cheat_enabled')
