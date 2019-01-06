from __future__ import annotations

from typing import Any, Dict, List, Callable, Coroutine, Iterable
from botus_receptus import abc, Config
from botus_receptus.gino import Bot

from discord.ext import commands
import discord
import logging
from itertools import chain

from .db.admin import GuildPrefs
from .context import Context
from .delay_queue import DelayQueue, DelayedAction

log = logging.getLogger(__name__)

extensions = ('mod', 'admin', 'roles')


class Bothanasius(
    Bot[Context],
    abc.OnCommandError[Context],
    abc.OnGuildJoin,
    abc.OnGuildAvailable,
    abc.OnGuildUnavailable,
):
    context_cls = Context
    prefix_map: Dict[int, str]

    delays: DelayQueue

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.prefix_map = {}

        super().__init__(config, *args, **kwargs)

        self.add_command(self.reload)

        for extension in extensions:
            try:
                self.load_extension(f'bothanasius.cogs.{extension}')
            except Exception:
                log.exception('Failed to load extension %s.', extension)

    async def close(self) -> None:
        if self.is_closed():
            return

        self.delays.stop()

        await super().close()

    async def get_prefix(self, message: discord.Message) -> str:
        if not message.guild:
            return self.default_prefix

        return self.prefix_map.get(message.guild.id, self.default_prefix)

    async def set_prefix(self, guild: discord.Guild, prefix: str) -> None:
        await GuildPrefs.set_prefix(guild, prefix)
        self.prefix_map[guild.id] = prefix

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx: Context, module: str) -> None:
        self.unload_extension(f'bothanasius.cogs.{module}')

        try:
            self.load_extension(f'bothanasius.cogs.{module}')
        except Exception:
            log.exception('Failed to load extension %s.', module)

    async def on_ready(self) -> None:
        all_prefs = await GuildPrefs.query.gino.all()
        self.dispatch('all_guild_prefs', all_prefs)

        actions: List[Iterable[DelayedAction]] = []
        for cog in self.cogs.values():
            try:
                get_actions: Callable[
                    [], Coroutine[Any, Any, List[DelayedAction]]
                ] = getattr(cog, f'_{cog.__class__.__name__}__get_delayed_actions')
                actions.append(await get_actions())
            except AttributeError:
                pass

        self.delays = DelayQueue.create(chain.from_iterable(actions), loop=self.loop)

    async def on_all_guild_prefs(self, all_prefs: List[GuildPrefs]) -> None:
        for prefs in all_prefs:
            self.prefix_map[prefs.guild_id] = prefs.prefix

    async def on_command_error(self, ctx: Context, error: Exception) -> None:
        if (
            isinstance(error, commands.BadArgument)
            or isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadUnionArgument)
        ):
            pages = await ctx.bot.formatter.format_help_for(ctx, ctx.command)

            await ctx.send_pages(pages)
            return

        await super().on_command_error(ctx, error)

    async def __setup_guild(
        self, guild: discord.Guild, *, joined: bool = False
    ) -> None:
        role = discord.utils.get(guild.roles, name='bothanasius-mute')

        if role is None:
            permissions = discord.Permissions()
            permissions.add_reactions = False
            permissions.external_emojis = False
            permissions.send_messages = False
            permissions.speak = False

            role = await guild.create_role(
                name='bothanasius-mute',
                permissions=permissions,
                reason='Added Bothanasius to the server',
            )

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
