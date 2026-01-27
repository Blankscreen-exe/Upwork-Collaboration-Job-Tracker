"""add_selected_allocations_to_receipts

Revision ID: a1b2c3d4e5f6
Revises: dd1eeec8ea78
Create Date: 2026-01-26 23:47:25.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '4a725ee46644'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('receipts')]
    
    if 'selected_allocation_ids' not in columns:
        # Add selected_allocation_ids column to receipts table
        # Store as Text (JSON string) for SQLite compatibility
        op.add_column('receipts', sa.Column('selected_allocation_ids', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove selected_allocation_ids column
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('receipts')]
    
    if 'selected_allocation_ids' in columns:
        op.drop_column('receipts', 'selected_allocation_ids')
