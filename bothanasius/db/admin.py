from __future__ import annotations

import discord
import argparse
import shlex
from typing import TYPE_CHECKING, Optional, NoReturn, Iterator
from mypy_extensions import TypedDict

import sqlalchemy
from botus_receptus.gino import Snowflake
from botus_receptus.util import parse_duration
from gino.dialects.asyncpg import JSONB

from .base import db, Base

if TYPE_CHECKING:
    from ..context import Context


class InvitePrefs(TypedDict):
    max_age: int
    max_uses: int
    temporary: bool
    unique: bool


class InviteArgumentParser(argparse.ArgumentParser):
    def __init__(self, defaults: InvitePrefs) -> None:
        super().__init__(add_help=False, allow_abbrev=False)
        self.add_argument('--max-age', nargs='+')
        self.add_argument('--max-uses', type=int)
        self.add_argument('--temporary', dest='temporary', action='store_true')
        self.add_argument('--not-temporary', dest='temporary', action='store_false')
        self.add_argument('--unique', dest='unique', action='store_true')
        self.add_argument('--not-unique', dest='unique', action='store_false')
        self.set_defaults(**defaults)

    def error(self, message: str) -> NoReturn:
        raise RuntimeError(message)

    @staticmethod
    async def parse(
        ctx: Context, defaults: InvitePrefs, args: str
    ) -> Optional[InvitePrefs]:
        parser = InviteArgumentParser(defaults)

        try:
            result = parser.parse_args(shlex.split(args))

            if isinstance(result.max_age, list):
                result.max_age = ' '.join(result.max_age)

            if isinstance(result.max_age, str):
                if result.max_age.isdigit():
                    result.max_age = int(result.max_age) * 60
                else:
                    result.max_age = parse_duration(result.max_age).in_seconds()

        except Exception as e:
            await ctx.send_error(str(e))
            return None

        return {
            'max_age': result.max_age,
            'max_uses': result.max_uses,
            'temporary': result.temporary,
            'unique': result.unique,
        }


if TYPE_CHECKING:
    InvitePrefsColumn = sqlalchemy.Column[InvitePrefs]
else:
    InvitePrefsColumn = sqlalchemy.Column


class GuildPrefs(Base):
    __tablename__ = 'guild_prefs'

    guild_id = db.Column(Snowflake(), primary_key=True)
    prefix = db.Column(db.String())
    mute_role = db.Column(Snowflake())
    admin_roles = db.Column(db.ARRAY(Snowflake()))
    mod_roles = db.Column(db.ARRAY(Snowflake()))

    invite_prefs: InvitePrefsColumn = db.Column(
        JSONB(),
        nullable=False,
        server_default='{"max_age": 0, "max_uses": 0, '
        '"temporary": false, "unique": true}',
    )
    max_age = db.IntegerProperty(prop_name='invite_prefs', default=0)
    max_uses = db.IntegerProperty(prop_name='invite_prefs', default=0)
    temporary = db.BooleanProperty(prop_name='invite_prefs', default=False)
    unique = db.BooleanProperty(prop_name='invite_prefs', default=True)

    time_out_role = db.Column(Snowflake())

    __guild: discord.Guild

    @property
    def guild(self) -> discord.Guild:
        return self.__guild

    @property
    def guild_admin_roles(self) -> Iterator[discord.Role]:
        return (
            filter(
                None,
                map(lambda role_id: self.__guild.get_role(role_id), self.admin_roles),
            )
            if self.admin_roles
            else iter([])
        )

    @property
    def guild_mod_roles(self) -> Iterator[discord.Role]:
        return (
            filter(
                None,
                map(lambda role_id: self.__guild.get_role(role_id), self.mod_roles),
            )
            if self.mod_roles
            else iter([])
        )

    @property
    def guild_mute_role(self) -> Optional[discord.Role]:
        mute_role = self.__guild.get_role(self.mute_role or -1)
        return (
            discord.utils.get(self.__guild.roles, name='Muted')
            if mute_role is None
            else mute_role
        )

    @property
    def guild_time_out_role(self) -> Optional[discord.Role]:
        time_out_role = self.__guild.get_role(self.time_out_role or -1)
        return (
            discord.utils.get(self.__guild.roles, name='Time Out')
            if time_out_role is None
            else time_out_role
        )

    async def add_admin_role(self, role: discord.Role) -> None:
        if self.admin_roles is not None and role.id in self.admin_roles:
            return

        await self.update(
            admin_roles=db.func.array_append(GuildPrefs.admin_roles, str(role.id))
        ).apply()

    async def remove_admin_role(self, role: discord.Role) -> None:
        await self.update(
            admin_roles=db.func.array_remove(GuildPrefs.admin_roles, str(role.id))
        ).apply()

    async def add_mod_role(self, role: discord.Role) -> None:
        if self.mod_roles is not None and role.id in self.mod_roles:
            return

        await self.update(
            mod_roles=db.func.array_append(GuildPrefs.mod_roles, str(role.id))
        ).apply()

    async def remove_mod_role(self, role: discord.Role) -> None:
        await self.update(
            mod_roles=db.func.array_remove(GuildPrefs.mod_roles, str(role.id))
        ).apply()

    async def set_mute_role(self, role: Optional[discord.Role]) -> None:
        if role is None:
            role = discord.utils.get(self.__guild.roles, name='Muted')

        await self.update(mute_role=role.id if role is not None else None).apply()

    @staticmethod
    async def for_guild(guild: discord.Guild) -> GuildPrefs:
        prefs = await GuildPrefs.query.where(
            GuildPrefs.guild_id == guild.id
        ).gino.first()
        assert prefs is not None

        prefs.__guild = guild

        return prefs
