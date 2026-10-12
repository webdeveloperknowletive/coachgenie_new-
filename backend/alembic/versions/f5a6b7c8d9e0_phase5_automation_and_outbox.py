"""phase5_automation_and_outbox

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-01 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. automation_rules table
    op.create_table(
        'automation_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auto_rules_tenant_active', 'automation_rules', ['tenant_id', 'rule_type', 'is_active'], unique=False)

    # 2. automation_events (Transactional Outbox) table
    op.create_table(
        'automation_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('scheduled_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('claimed_by', sa.String(length=100), nullable=True),
        sa.Column('claimed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('lease_expires_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auto_events_claim', 'automation_events', ['status', 'scheduled_at'], unique=False)
    op.create_index('idx_auto_events_tenant', 'automation_events', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_auto_events_lease', 'automation_events', ['status', 'lease_expires_at'], unique=False)

    # 3. automation_executions (Idempotency Ledger) table
    op.create_table(
        'automation_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SUCCEEDED'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('executed_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'idempotency_key', name='uq_tenant_idempotency')
    )
    op.create_index('idx_auto_exec_lookup', 'automation_executions', ['tenant_id', 'idempotency_key'], unique=False)
    op.create_index('idx_auto_exec_tenant_time', 'automation_executions', ['tenant_id', 'executed_at'], unique=False)

    # 4. web_push_subscriptions table
    op.create_table(
        'web_push_subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh_key', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'endpoint', name='uq_user_push_endpoint')
    )
    op.create_index('idx_webpush_tenant_user', 'web_push_subscriptions', ['tenant_id', 'user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_webpush_tenant_user', table_name='web_push_subscriptions')
    op.drop_table('web_push_subscriptions')
    op.drop_index('idx_auto_exec_tenant_time', table_name='automation_executions')
    op.drop_index('idx_auto_exec_lookup', table_name='automation_executions')
    op.drop_table('automation_executions')
    op.drop_index('idx_auto_events_lease', table_name='automation_events')
    op.drop_index('idx_auto_events_tenant', table_name='automation_events')
    op.drop_index('idx_auto_events_claim', table_name='automation_events')
    op.drop_table('automation_events')
    op.drop_index('idx_auto_rules_tenant_active', table_name='automation_rules')
    op.drop_table('automation_rules')
