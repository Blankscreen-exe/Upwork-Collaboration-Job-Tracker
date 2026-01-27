"""add_job_details_and_cover_letter

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('jobs')]
    
    # Add job source
    if 'source' not in columns:
        op.add_column('jobs', sa.Column('source', sa.String(), nullable=True))
    
    # Add description (HTML content from Quill.js)
    if 'description' not in columns:
        op.add_column('jobs', sa.Column('description', sa.Text(), nullable=True))
    
    # Add cover letter (HTML content from Quill.js)
    if 'cover_letter' not in columns:
        op.add_column('jobs', sa.Column('cover_letter', sa.Text(), nullable=True))
    
    # Add company/client details
    if 'company_name' not in columns:
        op.add_column('jobs', sa.Column('company_name', sa.String(), nullable=True))
    
    if 'company_website' not in columns:
        op.add_column('jobs', sa.Column('company_website', sa.String(), nullable=True))
    
    if 'company_email' not in columns:
        op.add_column('jobs', sa.Column('company_email', sa.String(), nullable=True))
    
    if 'company_phone' not in columns:
        op.add_column('jobs', sa.Column('company_phone', sa.String(), nullable=True))
    
    if 'company_address' not in columns:
        op.add_column('jobs', sa.Column('company_address', sa.Text(), nullable=True))
    
    if 'client_notes' not in columns:
        op.add_column('jobs', sa.Column('client_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove all added columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('jobs')]
    
    if 'client_notes' in columns:
        op.drop_column('jobs', 'client_notes')
    
    if 'company_address' in columns:
        op.drop_column('jobs', 'company_address')
    
    if 'company_phone' in columns:
        op.drop_column('jobs', 'company_phone')
    
    if 'company_email' in columns:
        op.drop_column('jobs', 'company_email')
    
    if 'company_website' in columns:
        op.drop_column('jobs', 'company_website')
    
    if 'company_name' in columns:
        op.drop_column('jobs', 'company_name')
    
    if 'cover_letter' in columns:
        op.drop_column('jobs', 'cover_letter')
    
    if 'description' in columns:
        op.drop_column('jobs', 'description')
    
    if 'source' in columns:
        op.drop_column('jobs', 'source')
