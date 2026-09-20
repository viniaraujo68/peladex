"""lowercase player and team names

Revision ID: c1d4f8a2b6e9
Revises: 92968730d785
Create Date: 2026-09-20 17:10:00.000000

"""
import re

import sqlalchemy as sa
from alembic import op

revision = 'c1d4f8a2b6e9'
down_revision = '92968730d785'
branch_labels = None
depends_on = None

TABLES = ('player', 'team')


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        rows = bind.execute(sa.text(f'SELECT id, name FROM "{table}"')).fetchall()
        for row_id, name in rows:
            lowered = re.sub(r'\s+', ' ', (name or '').strip()).lower()
            if lowered != name:
                bind.execute(
                    sa.text(f'UPDATE "{table}" SET name = :name WHERE id = :id'),
                    {'name': lowered, 'id': row_id},
                )


def downgrade() -> None:
    pass
