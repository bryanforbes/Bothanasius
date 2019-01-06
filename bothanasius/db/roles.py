from __future__ import annotations

import discord
from typing import List
from botus_receptus.gino import db, Snowflake, Base
from . import LtreeType


class LinkedRole(Base):
    __tablename__ = 'linked_roles'

    guild_id = db.Column(Snowflake(), primary_key=True)
    role_id = db.Column(Snowflake(), primary_key=True)
    path = db.Column(LtreeType(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('guild_id', 'role_id'),
        db.Index('linked_roles_path_gist_idx', 'path', postgresql_using='gist'),
    )


class SelfRole(Base):
    __tablename__ = 'self_roles'

    guild_id = db.Column(Snowflake(), primary_key=True)
    role_id = db.Column(Snowflake(), primary_key=True)

    __table_args__ = (db.UniqueConstraint('guild_id', 'role_id'),)

    @staticmethod
    async def delete_one(guild: discord.Guild, role: discord.Role) -> None:
        await SelfRole.delete.where(SelfRole.guild_id == guild.id).where(
            SelfRole.role_id == role.id
        ).gino.status()

    @staticmethod
    async def get_for_guild(guild: discord.Guild) -> List[SelfRole]:  # noqa
        return await SelfRole.query.where(SelfRole.guild_id == guild.id).gino.all()
