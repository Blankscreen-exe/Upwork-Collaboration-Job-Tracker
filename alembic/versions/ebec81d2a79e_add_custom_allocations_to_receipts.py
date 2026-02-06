"""add_custom_allocations_to_receipts

Revision ID: ebec81d2a79e
Revises: 7f0ae764d508
Create Date: 2026-02-07 00:28:31.521598

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ebec81d2a79e'
down_revision = '7f0ae764d508'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('receipts')]
    
    if 'use_custom_allocations' not in columns:
        op.add_column('receipts', sa.Column('use_custom_allocations', sa.Boolean(), nullable=True, server_default='0'))
        # Update existing rows to False
        op.execute("UPDATE receipts SET use_custom_allocations = 0 WHERE use_custom_allocations IS NULL")
    
    if 'custom_allocations' not in columns:
        op.add_column('receipts', sa.Column('custom_allocations', sa.Text(), nullable=True))


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('receipts')]
    
    if 'custom_allocations' in columns:
        op.drop_column('receipts', 'custom_allocations')
    
    if 'use_custom_allocations' in columns:
        op.drop_column('receipts', 'use_custom_allocations')
