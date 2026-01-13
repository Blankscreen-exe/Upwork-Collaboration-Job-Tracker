"""add_is_auto_generated_to_payments

Revision ID: d9f1cc37bf84
Revises: 
Create Date: 2026-01-12 23:01:59.996490

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9f1cc37bf84'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (in case of previous failed migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('payments')]
    
    if 'is_auto_generated' not in columns:
        # Add is_auto_generated column to payments table
        # SQLite uses INTEGER for booleans (0/1)
        # SQLite doesn't support ALTER COLUMN, so we add it as nullable with default
        op.add_column('payments', sa.Column('is_auto_generated', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    
    # Set default value to False (0) for existing records (safe to run multiple times)
    op.execute("UPDATE payments SET is_auto_generated = 0 WHERE is_auto_generated IS NULL")
    # Note: SQLite doesn't support changing nullability, but the server_default
    # and application-level default will ensure all values are set


def downgrade() -> None:
    # Remove is_auto_generated column
    op.drop_column('payments', 'is_auto_generated')
