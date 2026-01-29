"""add_expenses_table

Revision ID: d7835dd35fca
Revises: b2c3d4e5f6a7
Create Date: 2026-01-29 11:53:02.592728

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7835dd35fca'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'expenses' not in tables:
        op.create_table(
            'expenses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('expense_code', sa.String(), nullable=False),
            sa.Column('expense_date', sa.Date(), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=False),
            sa.Column('vendor', sa.String(), nullable=True),
            sa.Column('reference', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)
        op.create_index(op.f('ix_expenses_expense_code'), 'expenses', ['expense_code'], unique=True)


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'expenses' in tables:
        op.drop_index(op.f('ix_expenses_expense_code'), table_name='expenses')
        op.drop_index(op.f('ix_expenses_id'), table_name='expenses')
        op.drop_table('expenses')
