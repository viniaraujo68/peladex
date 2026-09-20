"""group default venue

Revision ID: 92968730d785
Revises: f604602fd3b6
Create Date: 2026-09-20 10:11:32.143574

"""
from alembic import op
import sqlalchemy as sa


revision = '92968730d785'
down_revision = 'f604602fd3b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_venue_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_group_default_venue_id_venue', 'venue', ['default_venue_id'], ['id']
        )



def downgrade() -> None:
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.drop_constraint('fk_group_default_venue_id_venue', type_='foreignkey')
        batch_op.drop_column('default_venue_id')

