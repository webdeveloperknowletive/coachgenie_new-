"""phase3_fee_installments

Revision ID: d3e4f5a6b7c8
Revises: c1a2e3f4b5d6
Create Date: 2026-09-01 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c1a2e3f4b5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create fee_installments table
    op.create_table(
        'fee_installments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('installment_no', sa.SmallInteger(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('amount_due', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['fee_invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_id', 'installment_no', name='uq_invoice_installment')
    )
    op.create_index('idx_inst_tenant_due', 'fee_installments', ['tenant_id', 'due_date', 'status'], unique=False)
    op.create_index('idx_inst_student', 'fee_installments', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_inst_student', table_name='fee_installments')
    op.drop_index('idx_inst_tenant_due', table_name='fee_installments')
    op.drop_table('fee_installments')
