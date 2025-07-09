"""Add auth_sessions table for persistent authentication

Revision ID: 9a64e8e698b4
Revises: 29e469a16a52
Create Date: 2025-07-09 18:24:23.864215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a64e8e698b4'
down_revision: Union[str, None] = '29e469a16a52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('auth_sessions',
        sa.Column('service_name', sa.String(50), nullable=False, primary_key=True),
        sa.Column('cookie_data', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('auth_sessions')