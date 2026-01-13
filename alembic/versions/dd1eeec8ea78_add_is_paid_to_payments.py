"""add_is_paid_to_payments

Revision ID: dd1eeec8ea78
Revises: d9f1cc37bf84
Create Date: 2026-01-12 23:23:22.624035

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd1eeec8ea78'
down_revision = 'd9f1cc37bf84'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (in case of previous failed migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('payments')]
    
    if 'is_paid' not in columns:
        # Add is_paid column to payments table
        # SQLite uses INTEGER for booleans (0/1)
        # SQLite doesn't support ALTER COLUMN, so we add it as nullable with default
        op.add_column('payments', sa.Column('is_paid', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    
    # Set default value to False (0) for existing records (safe to run multiple times)
    # For existing payments, assume they were paid (historical data)
    op.execute("UPDATE payments SET is_paid = 1 WHERE is_paid IS NULL")
    # Note: SQLite doesn't support changing nullability, but the server_default
    # and application-level default will ensure all values are set


def downgrade() -> None:
    # Remove is_paid column
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('payments')]
    
    if 'is_paid' in columns:
        op.drop_column('payments', 'is_paid')
