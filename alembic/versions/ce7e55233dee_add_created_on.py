"""Add created_on

Revision ID: ce7e55233dee
Revises: 73084a3640c5
Create Date: 2018-09-01 20:50:56.306593

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce7e55233dee'
down_revision = '73084a3640c5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('delayed_mutes', sa.Column('created_at', sa.DateTime))


def downgrade():
    op.drop_column('delayed_mutes', 'created_at')
