"""phase4_parent_user_link

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-01 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('students', sa.Column('parent_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_students_parent_user_id',
        'students', 'users',
        ['parent_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_students_parent_user', 'students', ['parent_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_students_parent_user', table_name='students')
    op.drop_constraint('fk_students_parent_user_id', 'students', type_='foreignkey')
    op.drop_column('students', 'parent_user_id')
