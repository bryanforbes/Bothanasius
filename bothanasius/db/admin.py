import discord

from sqlalchemy.dialects.postgresql import insert

from . import db, Snowflake, Base


class GuildPrefs(Base):
    __tablename__ = 'guild_prefs'

    guild_id = db.Column(db.Integer(), primary_key=True)
    prefix = db.Column(db.String())
    mute_role = db.Column(Snowflake())
    admin_roles = db.Column(db.ARRAY(Snowflake()))
    mod_roles = db.Column(db.ARRAY(Snowflake()))

    @staticmethod
    async def add_admin_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update \
            .values(admin_roles=db.func.array_append(GuildPrefs.admin_roles, str(role.id))) \
            .where(db.and_(GuildPrefs.guild_id == guild.id,
                           GuildPrefs.admin_roles.any(str(role.id)).isnot(True))) \
            .gino.status()

    @staticmethod
    async def remove_admin_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update \
            .values(admin_roles=db.func.array_remove(GuildPrefs.admin_roles, str(role.id))) \
            .where(GuildPrefs.guild_id == guild.id) \
            .gino.status()

    @staticmethod
    async def add_mod_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update \
            .values(mod_roles=db.func.array_append(GuildPrefs.mod_roles, str(role.id))) \
            .where(db.and_(GuildPrefs.guild_id == guild.id,
                           GuildPrefs.mod_roles.any(str(role.id)).isnot(True))) \
            .gino.status()

    @staticmethod
    async def remove_mod_role(guild: discord.Guild, role: discord.Role) -> None:
        await GuildPrefs.update \
            .values(mod_roles=db.func.array_remove(GuildPrefs.mod_roles, str(role.id))) \
            .where(GuildPrefs.guild_id == guild.id) \
            .gino.status()

    @staticmethod
    async def set_prefix(guild: discord.Guild, prefix: str) -> None:
        await GuildPrefs.update \
            .values(prefix=prefix) \
            .where(GuildPrefs.guild_id == guild.id) \
            .gino.status()

    @staticmethod
    async def create_or_update(guild: discord.Guild, prefix: str, role: discord.Role) -> None:
        stmt = insert(GuildPrefs).values(guild_id=guild.id,
                                         prefix=prefix,
                                         mute_role=role.id)
        stmt = stmt.on_conflict_do_update(index_elements=['guild_id'],
                                          set_=dict(prefix=stmt.excluded.prefix,
                                                    mute_role=stmt.excluded.mute_role))
        await db.scalar(stmt)
