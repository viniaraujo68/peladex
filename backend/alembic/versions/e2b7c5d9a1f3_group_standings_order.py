"""group standings order

Revision ID: e2b7c5d9a1f3
Revises: d7e3a1b9c4f2
Create Date: 2026-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = 'e2b7c5d9a1f3'
down_revision = 'd7e3a1b9c4f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'group',
        sa.Column('standings_order', sqlmodel.sql.sqltypes.AutoString(), nullable=False,
                  server_default='points'),
    )


def downgrade() -> None:
    op.drop_column('group', 'standings_order')
