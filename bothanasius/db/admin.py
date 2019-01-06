from __future__ import annotations

import discord

from botus_receptus.gino import db, Base, Snowflake, create_or_update


class GuildPrefs(Base):
    __tablename__ = 'guild_prefs'

    guild_id = db.Column(Snowflake(), primary_key=True)
    prefix = db.Column(db.String())
    mute_role = db.Column(Snowflake())
    admin_roles = db.Column(db.ARRAY(Snowflake()))
    mod_roles = db.Column(db.ARRAY(Snowflake()))

    @staticmethod
    async def add_admin_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update.values(
            admin_roles=db.func.array_append(GuildPrefs.admin_roles, str(role.id))
        ).where(
            db.and_(
                GuildPrefs.guild_id == guild.id,
                GuildPrefs.admin_roles.any(str(role.id)).isnot(True),
            )
        ).gino.status()

    @staticmethod
    async def remove_admin_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update.values(
            admin_roles=db.func.array_remove(GuildPrefs.admin_roles, str(role.id))
        ).where(GuildPrefs.guild_id == guild.id).gino.status()

    @staticmethod
    async def add_mod_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update.values(
            mod_roles=db.func.array_append(GuildPrefs.mod_roles, str(role.id))
        ).where(
            db.and_(
                GuildPrefs.guild_id == guild.id,
                GuildPrefs.mod_roles.any(str(role.id)).isnot(True),
            )
        ).gino.status()

    @staticmethod
    async def remove_mod_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update.values(
            mod_roles=db.func.array_remove(GuildPrefs.mod_roles, str(role.id))
        ).where(GuildPrefs.guild_id == guild.id).gino.status()

    @staticmethod
    async def set_prefix(guild: discord.Guild, prefix: str) -> None:
        await GuildPrefs.update.values(prefix=prefix).where(
            GuildPrefs.guild_id == guild.id
        ).gino.status()

    @staticmethod
    async def create_or_update(
        guild: discord.Guild, prefix: str, role: discord.Role
    ) -> GuildPrefs:  # noqa: F821
        return await create_or_update(
            GuildPrefs,
            set_=('prefix', 'mute_role'),
            guild_id=guild.id,
            prefix=prefix,
            mute_role=role.id,
        )
