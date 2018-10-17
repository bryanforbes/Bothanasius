from __future__ import annotations

from typing import Any, Dict, List, Sequence, Union, cast
from configparser import ConfigParser
from botus_receptus import abc, Bot
from asyncpg import Connection

from discord.ext import commands
import discord
import logging

from .db import db
from .db.admin import GuildPrefs
from .context import Context

log = logging.getLogger(__name__)

extensions = (
    'mod',
    'admin',
    'roles',
)


class Bothanasius(Bot[Context],
                  abc.OnCommandError[Context],
                  abc.OnGuildJoin,
                  abc.OnGuildAvailable,
                  abc.OnGuildUnavailable):
    context_cls = Context
    prefix_map: Dict[int, str]

    def __init__(self, config: ConfigParser, *args: Any, **kwargs: Any) -> None:
        self.prefix_map = {}

        super().__init__(config, *args, **kwargs)

        self.loop.run_until_complete(db.set_bind(self.config.get('bot', 'db_url')))

        self.add_command(self.reload)

        for extension in extensions:
            try:
                self.load_extension(f'bothanasius.cogs.{extension}')
            except Exception as e:
                log.exception('Failed to load extension %s.', extension)

    async def __init_connection__(self, conn: Connection) -> None:
        await conn.set_type_codec('ltree',
                                  encoder=self.__encode_ltree,
                                  decoder=self.__decode_ltree)

    def __encode_ltree(self, value: Union[str, Sequence[str]]) -> str:
        if isinstance(value, str):
            return value
        else:
            return '.'.join(value)

    def __decode_ltree(self, value: str) -> List[str]:
        return value.split('.')

    async def close(self) -> None:
        await cast(Any, db.pop_bind()).close()
        await super().close()

    async def get_prefix(self, message: discord.Message) -> str:
        if not message.guild:
            return self.default_prefix

        return self.prefix_map.get(message.guild.id, self.default_prefix)

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx: Context, module: str) -> None:
        self.unload_extension(f'bothanasius.cogs.{module}')

        try:
            self.load_extension(f'bothanasius.cogs.{module}')
        except Exception as e:
            log.exception('Failed to load extension %s.', module)

    async def set_prefix(self, ctx: Context, guild: discord.Guild, prefix: str) -> None:
        await GuildPrefs.set_prefix(guild, prefix)
        self.prefix_map[guild.id] = prefix

    async def on_ready(self) -> None:
        all_prefs = await GuildPrefs.query.gino.all()
        self.dispatch('all_guild_prefs', all_prefs)

    async def on_all_guild_prefs(self, all_prefs: List[GuildPrefs]) -> None:
        for prefs in all_prefs:
            self.prefix_map[prefs.guild_id] = prefs.prefix

    async def on_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, commands.BadArgument) or \
                isinstance(error, commands.MissingRequiredArgument) or \
                isinstance(error, commands.BadUnionArgument):
            pages = await ctx.bot.formatter.format_help_for(ctx, ctx.command)

            await ctx.send_pages(pages)
            return

        await super().on_command_error(ctx, error)

    async def __setup_guild(self, guild: discord.Guild, *, joined: bool = False) -> None:
        role = discord.utils.get(guild.roles, name='bothanasius-mute')

        if role is None:
            permissions = discord.Permissions()
            permissions.add_reactions = False
            permissions.external_emojis = False
            permissions.send_messages = False
            permissions.speak = False

            role = await guild.create_role(name='bothanasius-mute', permissions=permissions,
                                           reason='Added Bothanasius to the server')

        if joined:
            await GuildPrefs.create_or_update(guild, self.default_prefix, role)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.__setup_guild(guild, joined=True)

        log.info('Guild joined: %s', guild.id)

    async def on_guild_available(self, guild: discord.Guild) -> None:
        await self.__setup_guild(guild)

        log.info('Guild available: %s', guild.id)

    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        log.info('Guild unavailable: %s', guild.id)
