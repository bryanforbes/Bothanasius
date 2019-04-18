from __future__ import annotations

from botus_receptus import abc, Config
from botus_receptus.gino import Bot
from discord.ext import commands
from typing import Any, Optional, Union, Dict, Tuple, overload
from typing_extensions import Final

import asyncio
import asyncpg
import discord
import logging
import pendulum

from .db.base import db
from .db.admin import GuildPrefs
from .db.delayed_action import DelayedAction
from .context import Context

log = logging.getLogger(__name__)

# asyncio.sleep can only sleep for up to ~48 days reliably
# so we're gonna cap it off at 40 days
# see: http://bugs.python.org/issue20493
MAX_SLEEP_TIME: Final = 86400 * 40  # 40 days

extensions: Final = ('meta', 'admin', 'mod', 'roles')


class Bothanasius(
    Bot[Context],
    abc.OnCommandError[Context],
    abc.OnGuildJoin,
    abc.OnGuildAvailable,
    abc.OnGuildUnavailable,
):
    db = db
    context_cls = Context
    prefix_map: Dict[int, str]

    _task: 'asyncio.Task[None]'
    _have_data: asyncio.Event
    _current_action: Optional[DelayedAction]

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.prefix_map = {}

        super().__init__(config, *args, **kwargs)

        self._have_data = asyncio.Event(loop=self.loop)

        for extension in extensions:
            try:
                self.load_extension(f'bothanasius.cogs.{extension}')
            except Exception:
                log.exception('Failed to load extension %s.', extension)

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message)

        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def close(self) -> None:
        self._task.cancel()
        await super().close()

    async def get_prefix(self, message: discord.Message) -> str:
        if not message.guild:
            return self.default_prefix

        return self.prefix_map.get(message.guild.id, self.default_prefix)

    def get_guild_member(
        self, guild_id: int, member_id: int
    ) -> Union[
        Tuple[None, None],
        Tuple[discord.Guild, Optional[discord.Member]],
        Tuple[discord.Guild, discord.Member],
    ]:
        guild = self.get_guild(guild_id)

        if guild is None:
            return None, None

        member = guild.get_member(member_id)

        if member is None:
            return guild, None

        return guild, member

    async def __action_loop(self) -> None:
        try:
            while not self.is_closed():
                now = pendulum.now()
                action = self._current_action = await self.__wait_for_action()

                if action.expires >= now:
                    to_sleep = (action.expires - now).total_seconds()
                    print(f'waiting {to_sleep} seconds')
                    await asyncio.sleep(min(to_sleep, MAX_SLEEP_TIME))

                    if to_sleep > MAX_SLEEP_TIME:
                        print('rechecking after waiting max')
                        continue

                await self.__dispatch_action(action)
        except asyncio.CancelledError:
            pass
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.__restart_action_loop()

    def __restart_action_loop(self) -> None:
        if self._task:
            self._task.cancel()

        self._task = self.loop.create_task(self.__action_loop())

    async def __wait_for_action(self) -> DelayedAction:
        action = await DelayedAction.get_active()

        if action is not None:
            self._have_data.set()
            return action

        self._have_data.clear()
        self._current_action = None
        print('waiting for have_data')
        await self._have_data.wait()

        action = await DelayedAction.get_active()
        assert action is not None

        return action

    async def __dispatch_action(
        self, action: DelayedAction, *, seconds: Optional[float] = None
    ) -> None:
        if action.id != -1:
            await action.delete()

        if seconds is not None:
            await asyncio.sleep(seconds)

        self.dispatch(f'{action.event}_action_complete', action)

    async def create_action(
        self, when: pendulum.DateTime, event: str, *args: Any, **kwargs: Any
    ) -> DelayedAction:
        now = pendulum.now()
        delta = (when - now).total_seconds()

        if delta <= 60:
            action = DelayedAction(
                id=-1,
                created_at=now,
                expires=when,
                event=event,
                profile=dict(args=list(args), kwargs=kwargs),
            )
            # TODO: how to cancel these?
            self.loop.create_task(self.__dispatch_action(action, seconds=delta))
            return action

        action = await DelayedAction.create(
            created_at=now,
            expires=when,
            event=event,
            profile=dict(args=list(args), kwargs=kwargs),
        )

        if delta <= MAX_SLEEP_TIME:
            self._have_data.set()

        if self._current_action and when < self._current_action.expires:
            self.__restart_action_loop()

        return action

    async def create_or_update_action(
        self, when: pendulum.DateTime, event: str, *args: Any, **kwargs: Any
    ) -> DelayedAction:
        await DelayedAction.delete_by_event(event, *args)

        return await self.create_action(when, event, *args, **kwargs)

    async def get_action(self, event: str, *args: Any) -> Optional[DelayedAction]:
        return await DelayedAction.get_by_event(event, *args)

    @overload
    async def remove_action(self, event: str, *args: Any) -> None:
        ...

    @overload  # noqa: F811
    async def remove_action(self, event: DelayedAction) -> None:
        ...

    async def remove_action(  # noqa: F811
        self, event: Union[str, DelayedAction], *args: Any
    ) -> None:
        if isinstance(event, str):
            removed = await DelayedAction.delete_by_event(event, *args)
        else:
            await event.delete()
            removed = event

        if removed and self._current_action and removed.id == self._current_action.id:
            self.__restart_action_loop()

    async def on_ready(self) -> None:
        async with db.transaction():
            async for prefs in GuildPrefs.query.gino.iterate():
                if prefs.prefix is not None:
                    self.prefix_map[prefs.guild_id] = prefs.prefix

        self._task = self.loop.create_task(self.__action_loop())

    async def on_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, (commands.UserInputError, commands.ConversionError)):
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        else:
            await super().on_command_error(ctx, error)

    async def __setup_role(
        self,
        guild: discord.Guild,
        *,
        name: str,
        permissions: Dict[str, bool],
        reason: str,
    ) -> discord.Role:
        role = discord.utils.get(guild.roles, name=name)

        if role is None:
            role_perms = discord.Permissions()
            role_perms.update(**permissions)

            role = await guild.create_role(
                name=name, permissions=role_perms, reason=reason
            )

        return role

    async def __setup_guild(
        self, guild: discord.Guild, *, joined: bool = False
    ) -> None:
        mute_role = await self.__setup_role(
            guild,
            name='Muted',
            permissions=dict(
                add_reactions=False,
                external_emojis=False,
                send_messages=False,
                speak=False,
            ),
            reason='Bothanasius set up mute role',
        )

        time_out_role = await self.__setup_role(
            guild,
            name='Time Out',
            permissions=dict(read_messages=False),
            reason='Bothanasius set up time out role',
        )

        if joined:
            await GuildPrefs.create_or_update(
                guild_id=guild.id,
                prefix=self.default_prefix,
                mute_role=mute_role.id,
                time_out_role=time_out_role.id,
                set_=('prefix', 'mute_role', 'time_out_role'),
            )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.__setup_guild(guild, joined=True)

        log.info('Guild joined: %s', guild.id)

    async def on_guild_available(self, guild: discord.Guild) -> None:
        await self.__setup_guild(guild)

        log.info('Guild available: %s', guild.id)

    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        log.info('Guild unavailable: %s', guild.id)
