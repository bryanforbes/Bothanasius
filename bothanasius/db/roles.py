from __future__ import annotations

import discord
from typing import AsyncIterator
from botus_receptus.gino import Snowflake

from .base import db, Base


class SelfRole(Base):
    __tablename__ = 'self_roles'

    guild_id = db.Column(Snowflake(), primary_key=True)
    role_id = db.Column(Snowflake(), primary_key=True)

    __table_args__ = (
        db.UniqueConstraint(
            'guild_id', 'role_id', name='self_roles_guild_id_role_id_key'
        ),
    )

    @staticmethod
    async def delete_one(guild: discord.Guild, role: discord.Role) -> None:
        await SelfRole.delete.where(SelfRole.guild_id == guild.id).where(
            SelfRole.role_id == role.id
        ).gino.status()

    @staticmethod
    async def get_for_guild(guild: discord.Guild) -> AsyncIterator[SelfRole]:
        async with db.transaction():
            async for role in SelfRole.query.where(
                SelfRole.guild_id == guild.id
            ).gino.iterate():
                yield role
