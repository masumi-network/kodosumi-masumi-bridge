"""add_timeout_field

Revision ID: 29e469a16a52
Revises: 001
Create Date: 2025-07-02 15:51:00.572522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '29e469a16a52'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timeout_at column to flow_runs table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('flow_runs')]
    
    if 'timeout_at' not in columns:
        op.add_column('flow_runs', sa.Column('timeout_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove timeout_at column from flow_runs table
    op.drop_column('flow_runs', 'timeout_at')