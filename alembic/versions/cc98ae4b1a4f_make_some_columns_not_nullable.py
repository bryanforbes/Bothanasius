"""Make some columns not nullable

Revision ID: cc98ae4b1a4f
Revises: 7254a2072faf
Create Date: 2019-01-19 22:16:58.690737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc98ae4b1a4f'
down_revision = '7254a2072faf'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('delayed_mutes', 'end_time', nullable=False)
    op.alter_column('delayed_mutes', 'created_at', nullable=False)
    op.alter_column('warnings', 'guild_id', nullable=False)
    op.alter_column('warnings', 'member_id', nullable=False)
    op.alter_column('warnings', 'moderator_id', nullable=False)
    op.alter_column('warnings', 'timestamp', nullable=False)


def downgrade():
    op.alter_column('delayed_mutes', 'end_time', nullable=True)
    op.alter_column('delayed_mutes', 'created_at', nullable=True)
    op.alter_column('warnings', 'guild_id', nullable=True)
    op.alter_column('warnings', 'member_id', nullable=True)
    op.alter_column('warnings', 'moderator_id', nullable=True)
    op.alter_column('warnings', 'timestamp', nullable=True)
