"""Add self-roles

Revision ID: 73084a3640c5
Revises: c7b49d6f2948
Create Date: 2018-07-07 12:29:55.640225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73084a3640c5'
down_revision = 'c7b49d6f2948'
branch_labels = None
depends_on = None


class LTreeType(sa.types.UserDefinedType):
    def get_col_spec(self, **kwargs):
        return 'ltree'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process


def upgrade():
    op.execute('CREATE EXTENSION ltree')
    op.create_table('self_roles',
                    sa.Column('guild_id', sa.String, primary_key=True),
                    sa.Column('role_id', sa.String, primary_key=True),
                    sa.UniqueConstraint('guild_id', 'role_id'))
    op.create_table('linked_roles',
                    sa.Column('guild_id', sa.String, primary_key=True),
                    sa.Column('role_id', sa.String, primary_key=True),
                    sa.Column('path', LTreeType, nullable=False),
                    sa.Column('parent_role_id', sa.String),
                    sa.UniqueConstraint('guild_id', 'role_id'))

    op.create_index('linked_roles_parent_role_idx', 'linked_roles', ['guild_id', 'parent_role_id'])
    op.create_index('linked_roles_path_gist_idx', 'linked_roles', ['path'], postgresql_using='gist')


def downgrade():
    op.drop_index('linked_roles_path_gist_idx', 'linked_roles')
    op.drop_index('linked_roles_parent_role_idx', 'linked_roles')
    op.drop_table('linked_roles')
    op.drop_table('self_roles')
    op.execute('DROP EXTENSION ltree')
