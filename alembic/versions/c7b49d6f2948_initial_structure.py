"""Initial structure

Revision ID: c7b49d6f2948
Revises: 
Create Date: 2018-06-04 14:56:09.879629

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c7b49d6f2948'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('guild_prefs',
                    sa.Column('guild_id', sa.String, primary_key=True),
                    sa.Column('prefix', sa.String),
                    sa.Column('mute_role', sa.String),
                    sa.Column('admin_roles', postgresql.ARRAY(sa.String)),
                    sa.Column('mod_roles', postgresql.ARRAY(sa.String)))

    op.create_table('delayed_mutes',
                    sa.Column('guild_id', sa.String, primary_key=True),
                    sa.Column('member_id', sa.String, primary_key=True),
                    sa.Column('end_time', sa.DateTime))

    op.create_table('warnings',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('guild_id', sa.String),
                    sa.Column('member_id', sa.String),
                    sa.Column('moderator_id', sa.String),
                    sa.Column('reason', sa.String, nullable=True),
                    sa.Column('timestamp', sa.DateTime),
                    sa.Column('cleared_on', sa.DateTime, nullable=True),
                    sa.Column('cleared_by', sa.String, nullable=True))

    op.create_index('warnings_guild_idx', 'warnings', ['guild_id'])
    op.create_index('warnings_guild_member_idx', 'warnings', ['guild_id', 'member_id'])


def downgrade():
    op.drop_index('warnings_guild_member_idx', 'warnings')
    op.drop_index('warnings_guild_idx', 'warnings')
    op.drop_table('warnings')
    op.drop_table('delayed_mutes')
    op.drop_table('guild_prefs')
