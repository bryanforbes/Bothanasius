"""Add invite_prefs column

Revision ID: 7254a2072faf
Revises: ce7e55233dee
Create Date: 2019-01-06 16:24:34.243915

"""
from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '7254a2072faf'
down_revision = 'ce7e55233dee'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'guild_prefs',
        sa.Column(
            'invite_prefs',
            JSONB,
            nullable=False,
            server_default='{"max_age": 0, "max_uses": 0, '
            '"temporary": false, "unique": true}',
        ),
    )


def downgrade():
    op.drop_column('guild_prefs', 'invite_prefs')
