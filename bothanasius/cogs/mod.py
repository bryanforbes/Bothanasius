from __future__ import annotations

from typing import Any, Optional, Union, overload

import attr
import discord
import logging

from itertools import tee, filterfalse
from discord.ext import commands
from datetime import datetime, timedelta
from botus_receptus.formatting import EmbedPaginator, underline, bold, strikethrough

from ..bothanasius import Bothanasius
from ..delay_queue import DelayQueue
from ..db.mod import DelayedMute, Warning
from ..context import Context, GuildContext

log = logging.getLogger(__name__)


@attr.s(slots=True, auto_attribs=True)
class Unmute(object):
    guild_id: int
    member_id: int
    created_at: datetime
    end_time: datetime


@attr.s(slots=True, auto_attribs=True)
class Moderation(object):
    bot: Bothanasius
    __weakref__: Any = attr.ib(init=False, hash=False, repr=False, cmp=False)

    queue: DelayQueue[Unmute] = attr.ib(init=False)

    def __unload(self) -> None:
        self.queue.stop()

    async def __local_check(self, ctx: Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.guild.owner != ctx.author and not await ctx.has_mod_role():
            return False

        return True

    async def __run_action(self, action: Unmute) -> None:
        await DelayedMute.delete_one(guild_id=action.guild_id,
                                     member_id=action.member_id)
        await self.__unmute(action.guild_id, action.member_id,
                            (action.end_time - action.created_at).total_seconds())

    @overload
    async def __unmute(self, guild_id: int, member_id: int, seconds: float) -> None: ...

    @overload  # noqa: F811
    async def __unmute(self, guild_id: discord.Guild, member_id: discord.Member,
                       seconds: float) -> None: ...

    async def __unmute(self, guild_id: Union[int, discord.Guild], member_id: Union[int, discord.Member],  # noqa: F811
                       seconds: float) -> None:
        guild = self.bot.get_guild(guild_id) if isinstance(guild_id, int) else guild_id

        if guild is not None:
            member = guild.get_member(member_id) if isinstance(member_id, int) else member_id

            if member is not None:
                role = discord.utils.get(guild.roles, name='bothanasius-mute')
                if role is not None:
                    if seconds is None:
                        reason = 'after bot restart'
                    else:
                        reason = f'after {seconds} seconds'
                    await member.remove_roles(role, reason=f'Unmuted {reason}')
                    log.info(f'{member_id} has been unmuted {reason}')

    async def on_ready(self) -> None:
        delayed_mutes = await DelayedMute.get_all_ascending()

        now = datetime.now()
        i1, i2 = tee(delayed_mutes)

        def predicate(delay: DelayedMute) -> bool:
            return delay.end_time <= now

        delays = filterfalse(predicate, i1)
        unmutes = filter(predicate, i2)

        self.queue = DelayQueue.create([Unmute(guild_id=delay.guild_id,
                                               member_id=delay.member_id,
                                               created_at=delay.created_at,
                                               end_time=delay.end_time) for delay in delays],
                                       self.__run_action,
                                       self.bot.loop)

        await DelayedMute.delete_prior_to(now)

        for unmute in unmutes:
            await self.__unmute(unmute.guild_id, unmute.member_id, unmute.seconds)

    @commands.command()
    async def mute(self, ctx: GuildContext, members: commands.Greedy[discord.Member],
                   minutes: Optional[int] = None) -> None:
        role = discord.utils.get(ctx.guild.roles, name='bothanasius-mute')

        if role is not None:
            if minutes is not None:
                now = datetime.now()
                end_time = now + timedelta(seconds=minutes * 60)

            for member in members:
                try:
                    await member.add_roles(role, reason=f'Muted by {ctx.message.author}')
                except discord.Forbidden:
                    await ctx.send_error(f'Could not mute {member.mention}. Please make sure the "Bothanasius" role is '
                                         'higher than the "bothanasius-mute" role.',
                                         title='Permissions incorrect')
                else:
                    await ctx.send_response(f'{member.mention} has been muted')

                    if minutes is None:
                        self.queue.find_and_remove(guild_id=ctx.guild.id, member_id=member.id)
                        await DelayedMute.delete_one(guild_id=ctx.guild.id,
                                                     member_id=member.id)
                    else:
                        self.queue.add(Unmute(ctx.guild.id, member.id, end_time, now))
                        await DelayedMute.create_or_update(guild=ctx.guild,
                                                           member=member,
                                                           end_time=end_time,
                                                           created_at=now)

    @commands.command()
    async def unmute(self, ctx: GuildContext, member: discord.Member) -> None:
        role = discord.utils.get(ctx.guild.roles, name='bothanasius-mute')

        if role is not None:
            self.queue.find_and_remove(guild_id=ctx.guild.id, member_id=member.id)
            await DelayedMute.delete_one(guild_id=ctx.guild.id,
                                         member_id=member.id)

            try:
                await member.remove_roles(role, reason=f'Unmuted by {ctx.message.author}')
            except discord.Forbidden:
                await ctx.send_error(f'Could not unmute {member.mention}. Please make sure the "Bothanasius" role is '
                                     'higher than the "bothanasius-mute" role.',
                                     title='Permissions incorrect')
            else:
                await ctx.send_response(f'{member.mention} has been unmuted')

    @commands.command()
    async def warn(self, ctx: GuildContext, member: discord.Member, *, reason: Optional[str] = None) -> None:
        await Warning.create(guild_id=ctx.guild.id,
                             member_id=member.id,
                             moderator_id=ctx.author.id,
                             reason=reason,
                             timestamp=datetime.now())

    @commands.command()
    async def warnings(self, ctx: GuildContext, member: Optional[discord.Member] = None) -> None:
        paginator = EmbedPaginator()
        title = 'Guild Warnings'

        if member is None:
            counts = await Warning.get_guild_counts(ctx.guild)

            for member_id, active, total in counts:
                member = ctx.guild.get_member(member_id)
                if member is not None:
                    paginator.add_line(f'{member}: {active} ({total - active} cleared)')
        else:
            title = f'Warnings for {member}'
            warnings = await Warning.get_for_member(ctx.guild, member)

            for warning in warnings:
                timestamp = warning.timestamp
                moderator = ctx.bot.get_user(warning.moderator_id) or warning.moderator_id

                warning_title = underline(bold(f'ID: {warning.id}'))

                if warning.cleared_by is not None:
                    warning_title = strikethrough(warning_title)

                paginator.add_line(warning_title)
                paginator.add_line(f'\t{bold("Date:")} {timestamp.strftime("%b %e %Y %H:%M:%S")}')
                paginator.add_line(f'\t{bold("Moderator:")} {moderator}')
                paginator.add_line(f'\t{bold("Reason:")} {warning.reason}', empty=warning.cleared_by is None)

                if warning.cleared_by is not None and warning.cleared_on is not None:
                    cleared_by = ctx.bot.get_user(int(warning.cleared_by)) or warning.cleared_by
                    paginator.add_line(f'\t{bold("Cleared by:")} {cleared_by}')
                    paginator.add_line(f'\t{bold("Cleared on:")} {warning.cleared_on.strftime("%b %e %Y %H:%M:%S")}',
                                       empty=True)

        page = None

        for page in paginator:
            await ctx.send_response(page, title=title)

        if page is None:
            if member is None:
                await ctx.send_response('No one has been warned')
            else:
                await ctx.send_response(f'{member} has not been warned')

    @commands.command()
    async def clearwarns(self, ctx: GuildContext, member: discord.Member, id: Optional[int] = None) -> None:
        if id is None:
            await Warning.clear_all(ctx.guild, member, ctx.author.id)
            await ctx.send_response(f'Warnings cleared for {member}')
        else:
            await Warning.clear_one(ctx.guild, member, id, ctx.author.id)
            await ctx.send_response(f'Warning {id} cleared for {member}')

    @commands.command()
    async def kick(self, ctx: GuildContext, member: discord.Member, reason: Optional[str] = None) -> None:
        await ctx.guild.kick(member, reason=reason)
        await ctx.send_response(f'{member.name} ({member}) has been kicked')

    @commands.command()
    async def ban(self, ctx: GuildContext, user: discord.User, reason: Optional[str] = None) -> None:
        await ctx.guild.ban(user, reason=reason)
        await ctx.send_response(f'{user.name} ({user}) has been banned')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Moderation(bot))
