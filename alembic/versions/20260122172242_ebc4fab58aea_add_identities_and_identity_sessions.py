"""add_identities_and_identity_sessions

Revision ID: ebc4fab58aea
Revises: 2d2db34d8d48
Create Date: 2026-01-22 17:22:42.104460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ebc4fab58aea'
down_revision: Union[str, Sequence[str], None] = '2d2db34d8d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the identity_kind enum type
    identity_kind = postgresql.ENUM(
        'DEVICE', 'STEAM', 'CUSTOM',
        name='identity_kind',
        create_type=False,
    )
    identity_kind.create(op.get_bind(), checkfirst=True)

    op.create_table('identities',
    sa.Column('account_id', sa.Uuid(), nullable=False),
    sa.Column('game_id', sa.Uuid(), nullable=False),
    sa.Column('kind', identity_kind, nullable=False),
    sa.Column('external_key', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identities_account_id'), 'identities', ['account_id'], unique=False)
    op.create_index(op.f('ix_identities_game_id'), 'identities', ['game_id'], unique=False)
    op.create_index('ix_identities_unique', 'identities', ['account_id', 'game_id', 'kind', 'external_key'], unique=True)
    op.create_table('identity_sessions',
    sa.Column('identity_id', sa.Uuid(), nullable=False),
    sa.Column('access_token_hash', sa.String(), nullable=False),
    sa.Column('refresh_token_hash', sa.String(), nullable=False),
    sa.Column('token_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('refresh_expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ip_address', sa.String(), nullable=True),
    sa.Column('user_agent', sa.String(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['identity_id'], ['identities.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_sessions_access_token_hash'), 'identity_sessions', ['access_token_hash'], unique=False)
    op.create_index(op.f('ix_identity_sessions_expires_at'), 'identity_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_identity_sessions_identity_id'), 'identity_sessions', ['identity_id'], unique=False)
    op.create_index(op.f('ix_identity_sessions_refresh_expires_at'), 'identity_sessions', ['refresh_expires_at'], unique=False)
    op.create_index(op.f('ix_identity_sessions_refresh_token_hash'), 'identity_sessions', ['refresh_token_hash'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_identity_sessions_refresh_token_hash'), table_name='identity_sessions')
    op.drop_index(op.f('ix_identity_sessions_refresh_expires_at'), table_name='identity_sessions')
    op.drop_index(op.f('ix_identity_sessions_identity_id'), table_name='identity_sessions')
    op.drop_index(op.f('ix_identity_sessions_expires_at'), table_name='identity_sessions')
    op.drop_index(op.f('ix_identity_sessions_access_token_hash'), table_name='identity_sessions')
    op.drop_table('identity_sessions')
    op.drop_index('ix_identities_unique', table_name='identities')
    op.drop_index(op.f('ix_identities_game_id'), table_name='identities')
    op.drop_index(op.f('ix_identities_account_id'), table_name='identities')
    op.drop_table('identities')

    # Drop the enum type
    postgresql.ENUM(name='identity_kind').drop(op.get_bind(), checkfirst=True)
