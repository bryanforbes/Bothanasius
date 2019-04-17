from __future__ import annotations

from botus_receptus.gino import Snowflake

from . import LtreeType
from .base import db, Base


class LinkedRole(Base):
    __tablename__ = 'linked_roles'

    guild_id = db.Column(Snowflake(), primary_key=True)
    role_id = db.Column(Snowflake(), primary_key=True)
    path = db.Column(LtreeType(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'guild_id', 'role_id', name='linked_roles_guild_id_role_id_key'
        ),
        db.Index('linked_roles_path_gist_idx', 'path', postgresql_using='gist'),
    )
