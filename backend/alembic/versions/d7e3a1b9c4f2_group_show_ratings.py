"""group show ratings

Revision ID: d7e3a1b9c4f2
Revises: c1d4f8a2b6e9
Create Date: 2026-09-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e3a1b9c4f2'
down_revision = 'c1d4f8a2b6e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'group',
        sa.Column('show_ratings', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('group', 'show_ratings')
