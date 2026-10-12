"""phase1_rbac_audit_custom_fields

Revision ID: c1a2e3f4b5d6
Revises: ffb6954a2ad5
Create Date: 2026-09-01 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1a2e3f4b5d6'
down_revision: Union[str, None] = 'ffb6954a2ad5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create custom_roles table
    op.create_table(
        'custom_roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_custom_roles_tenant_name')
    )
    op.create_index('idx_custom_roles_tenant', 'custom_roles', ['tenant_id'], unique=False)
    op.create_index('idx_custom_roles_active', 'custom_roles', ['tenant_id', 'is_active'], unique=False)

    # 2. Add custom_role_id to users
    op.add_column('users', sa.Column('custom_role_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_users_custom_role', 'users', 'custom_roles', ['custom_role_id'], ['id'], ondelete='SET NULL')

    # 3. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_tenant', 'audit_logs', ['tenant_id'], unique=False)
    op.create_index('idx_audit_actor', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('idx_audit_created_at', 'audit_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_audit_entity', 'audit_logs', ['tenant_id', 'entity_type', 'entity_id'], unique=False)

    # 4. Add custom_fields to students, leads, admissions, batches
    op.add_column('students', sa.Column('custom_fields', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('leads', sa.Column('custom_fields', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('admissions', sa.Column('custom_fields', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('batches', sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))


def downgrade() -> None:
    op.drop_column('batches', 'custom_fields')
    op.drop_column('admissions', 'custom_fields')
    op.drop_column('leads', 'custom_fields')
    op.drop_column('students', 'custom_fields')

    op.drop_index('idx_audit_entity', table_name='audit_logs')
    op.drop_index('idx_audit_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_actor', table_name='audit_logs')
    op.drop_index('idx_audit_tenant', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_constraint('fk_users_custom_role', 'users', type_='foreignkey')
    op.drop_column('users', 'custom_role_id')

    op.drop_index('idx_custom_roles_active', table_name='custom_roles')
    op.drop_index('idx_custom_roles_tenant', table_name='custom_roles')
    op.drop_table('custom_roles')
