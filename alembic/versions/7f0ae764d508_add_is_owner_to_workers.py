"""add_is_owner_to_workers

Revision ID: 7f0ae764d508
Revises: d7835dd35fca
Create Date: 2026-01-29 14:26:35.502821

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f0ae764d508'
down_revision = 'd7835dd35fca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('workers')]
    
    if 'is_owner' not in columns:
        op.add_column('workers', sa.Column('is_owner', sa.Boolean(), nullable=True, server_default='0'))
        # Update existing rows to False
        op.execute("UPDATE workers SET is_owner = 0 WHERE is_owner IS NULL")


def downgrade() -> None:
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('workers')]
    
    if 'is_owner' in columns:
        op.drop_column('workers', 'is_owner')
