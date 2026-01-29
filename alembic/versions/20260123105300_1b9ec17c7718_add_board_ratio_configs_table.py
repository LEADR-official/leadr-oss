"""add_board_ratio_configs_table

Revision ID: 1b9ec17c7718
Revises: d753d8fffd41
Create Date: 2026-01-23 10:53:00.053024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1b9ec17c7718'
down_revision: Union[str, Sequence[str], None] = 'd753d8fffd41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types with safe flags
    zero_denominator_policy = postgresql.ENUM(
        'NULL', 'ZERO', 'INFINITY',
        name='zero_denominator_policy',
        create_type=False
    )
    zero_denominator_policy.create(op.get_bind(), checkfirst=True)

    ratio_display = postgresql.ENUM(
        'RAW', 'PERCENT',
        name='ratio_display',
        create_type=False
    )
    ratio_display.create(op.get_bind(), checkfirst=True)

    tie_breaker = postgresql.ENUM(
        'NUMERATOR_DESC_DENOMINATOR_ASC',
        name='tie_breaker',
        create_type=False
    )
    tie_breaker.create(op.get_bind(), checkfirst=True)

    # Create the table
    op.create_table('board_ratio_configs',
        sa.Column('board_id', sa.Uuid(), nullable=False),
        sa.Column('numerator_board_id', sa.Uuid(), nullable=False),
        sa.Column('denominator_board_id', sa.Uuid(), nullable=False),
        sa.Column('zero_denominator_policy', zero_denominator_policy, server_default='NULL', nullable=False),
        sa.Column('min_denominator', sa.Float(), nullable=False),
        sa.Column('min_numerator', sa.Float(), nullable=False),
        sa.Column('scale', sa.Integer(), nullable=False),
        sa.Column('display', ratio_display, server_default='RAW', nullable=False),
        sa.Column('decimals', sa.Integer(), nullable=False),
        sa.Column('tie_breaker', tie_breaker, server_default='NUMERATOR_DESC_DENOMINATOR_ASC', nullable=False),
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['denominator_board_id'], ['boards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['numerator_board_id'], ['boards.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('board_id', name='uq_board_ratio_config_board')
    )
    op.create_index(op.f('ix_board_ratio_configs_board_id'), 'board_ratio_configs', ['board_id'], unique=False)
    op.create_index(op.f('ix_board_ratio_configs_denominator_board_id'), 'board_ratio_configs', ['denominator_board_id'], unique=False)
    op.create_index(op.f('ix_board_ratio_configs_numerator_board_id'), 'board_ratio_configs', ['numerator_board_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_board_ratio_configs_numerator_board_id'), table_name='board_ratio_configs')
    op.drop_index(op.f('ix_board_ratio_configs_denominator_board_id'), table_name='board_ratio_configs')
    op.drop_index(op.f('ix_board_ratio_configs_board_id'), table_name='board_ratio_configs')
    op.drop_table('board_ratio_configs')

    # Drop enum types safely
    postgresql.ENUM(name='tie_breaker').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='ratio_display').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='zero_denominator_policy').drop(op.get_bind(), checkfirst=True)
