"""assists and group tracking options

Revision ID: f604602fd3b6
Revises: 1a8e9062d137
Create Date: 2026-09-20 00:48:51.754690

"""
from alembic import op
import sqlalchemy as sa

revision = 'f604602fd3b6'
down_revision = '1a8e9062d137'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('goal', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assist_player_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_goal_assist_player_id'), ['assist_player_id'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_goal_assist_player_id_player', 'player', ['assist_player_id'], ['id']
        )

    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('track_scorers', sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column('track_assists', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.drop_column('track_assists')
        batch_op.drop_column('track_scorers')

    with op.batch_alter_table('goal', schema=None) as batch_op:
        batch_op.drop_constraint('fk_goal_assist_player_id_player', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_goal_assist_player_id'))
        batch_op.drop_column('assist_player_id')
