"""add_board_type_enum_and_column

Revision ID: 86a8f50de7ed
Revises: ebc4fab58aea
Create Date: 2026-01-22 18:19:19.648182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '86a8f50de7ed'
down_revision: Union[str, Sequence[str], None] = 'ebc4fab58aea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the board_type enum type
    board_type_enum = postgresql.ENUM(
        'RUN_IDENTITY', 'RUN_RUNS', 'COUNTER', 'RATIO',
        name='board_type',
        create_type=False,
    )
    board_type_enum.create(op.get_bind(), checkfirst=True)

    # Create the keep_strategy enum type
    keep_strategy_enum = postgresql.ENUM(
        'FIRST', 'BEST', 'LATEST', 'NA',
        name='keep_strategy',
        create_type=False,
    )
    keep_strategy_enum.create(op.get_bind(), checkfirst=True)

    # Migrate existing keep_strategy values from old names to new names
    # ALL -> BEST, FIRST_ONLY -> FIRST, BEST_ONLY -> BEST, LATEST_ONLY -> LATEST
    op.execute("UPDATE boards SET keep_strategy = 'BEST' WHERE keep_strategy = 'ALL'")
    op.execute("UPDATE boards SET keep_strategy = 'FIRST' WHERE keep_strategy = 'FIRST_ONLY'")
    op.execute("UPDATE boards SET keep_strategy = 'BEST' WHERE keep_strategy = 'BEST_ONLY'")
    op.execute("UPDATE boards SET keep_strategy = 'LATEST' WHERE keep_strategy = 'LATEST_ONLY'")
    op.execute("UPDATE board_templates SET keep_strategy = 'BEST' WHERE keep_strategy = 'ALL'")
    op.execute("UPDATE board_templates SET keep_strategy = 'FIRST' WHERE keep_strategy = 'FIRST_ONLY'")
    op.execute("UPDATE board_templates SET keep_strategy = 'BEST' WHERE keep_strategy = 'BEST_ONLY'")
    op.execute("UPDATE board_templates SET keep_strategy = 'LATEST' WHERE keep_strategy = 'LATEST_ONLY'")

    # Add board_type column to boards
    op.add_column(
        'boards',
        sa.Column(
            'board_type',
            board_type_enum,
            nullable=False,
            server_default='RUN_IDENTITY',
        )
    )

    # Add board_type column to board_templates
    op.add_column(
        'board_templates',
        sa.Column(
            'board_type',
            board_type_enum,
            nullable=False,
            server_default='RUN_IDENTITY',
        )
    )

    # Convert boards.keep_strategy from String to enum
    op.alter_column(
        'boards',
        'keep_strategy',
        type_=keep_strategy_enum,
        postgresql_using='keep_strategy::keep_strategy',
    )

    # Convert board_templates.keep_strategy from String to enum
    op.alter_column(
        'board_templates',
        'keep_strategy',
        type_=keep_strategy_enum,
        postgresql_using='keep_strategy::keep_strategy',
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Convert boards.keep_strategy back to String
    op.alter_column(
        'boards',
        'keep_strategy',
        type_=sa.String(),
        postgresql_using='keep_strategy::text',
    )

    # Convert board_templates.keep_strategy back to String
    op.alter_column(
        'board_templates',
        'keep_strategy',
        type_=sa.String(),
        postgresql_using='keep_strategy::text',
    )

    # Drop board_type columns
    op.drop_column('boards', 'board_type')
    op.drop_column('board_templates', 'board_type')

    # Drop enum types
    postgresql.ENUM(name='board_type').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='keep_strategy').drop(op.get_bind(), checkfirst=True)
