from __future__ import annotations

from typing import (
    Any,
    Optional,
    Union,
    Callable,
    Coroutine,
    Tuple,
    Type,
    List,
    overload,
)

import attr
import discord
import logging
import pendulum

from more_itertools import partition
from discord.ext import commands
from botus_receptus.formatting import EmbedPaginator, underline, bold, strikethrough

from ..bothanasius import Bothanasius
from ..db.admin import GuildPrefs
from ..db.mod import DelayedMute, Warning
from ..context import Context, GuildContext

log = logging.getLogger(__name__)


@attr.s(slots=True, auto_attribs=True, frozen=True)
class Unmute(object):
    guild_id: int
    member_id: int
    created_at: pendulum.DateTime
    end_time: pendulum.DateTime
    callback: Callable[['Unmute'], Coroutine[Any, Any, None]] = attr.ib(repr=False)

    @property
    def run(self) -> Callable[['Unmute'], Coroutine[Any, Any, None]]:
        return self.callback

    @property
    def id_key(self) -> Tuple[Type['Unmute'], Tuple[int, int]]:
        return Unmute, (self.guild_id, self.member_id)


@attr.s(slots=True, auto_attribs=True)
class Moderation(object):
    bot: Bothanasius

    async def __local_check(self, ctx: Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.guild.owner != ctx.author and not await ctx.has_mod_role():
            return False

        return True

    async def __run_action(self, action: Unmute) -> None:
        await DelayedMute.delete_one(
            guild_id=action.guild_id, member_id=action.member_id
        )
        await self.__unmute(
            action.guild_id,
            action.member_id,
            (action.end_time - action.created_at).total_seconds(),
        )

    async def __get_delayed_actions(self) -> List[Unmute]:
        delayed_mutes = await DelayedMute.get_all_ascending()

        now = pendulum.now()

        def predicate(delay: DelayedMute) -> bool:
            return delay.end_time <= now

        delays, unmutes = partition(predicate, delayed_mutes)

        await DelayedMute.delete_prior_to(now)

        for unmute in unmutes:
            await self.__unmute(unmute.guild_id, unmute.member_id, unmute.seconds)

        return [
            Unmute(
                guild_id=delay.guild_id,
                member_id=delay.member_id,
                created_at=pendulum.instance(delay.created_at),
                end_time=pendulum.instance(delay.end_time),
                callback=self.__run_action,
            )
            for delay in delays
        ]

    async def __get_mute_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        guild_prefs = await GuildPrefs.query.where(
            GuildPrefs.guild_id == guild.id
        ).gino.first()
        return (
            guild.get_role(guild_prefs.mute_role)
            if guild_prefs is not None
            else discord.utils.get(guild.roles, name='bothanasius-mute')
        )

    @overload
    async def __unmute(self, guild_id: int, member_id: int, seconds: float) -> None:
        ...

    @overload  # noqa: F811
    async def __unmute(
        self, guild_id: discord.Guild, member_id: discord.Member, seconds: float
    ) -> None:
        ...

    async def __unmute(  # noqa: F811
        self,
        guild_id: Union[int, discord.Guild],
        member_id: Union[int, discord.Member],
        seconds: float,
    ) -> None:
        guild = self.bot.get_guild(guild_id) if isinstance(guild_id, int) else guild_id

        if guild is not None:
            member = (
                guild.get_member(member_id) if isinstance(member_id, int) else member_id
            )

            if member is not None:
                role = await self.__get_mute_role(guild)
                if role is not None:
                    if seconds is None:
                        reason = 'after bot restart'
                    else:
                        reason = f'after {seconds} seconds'
                    await member.remove_roles(role, reason=f'Unmuted {reason}')
                    log.info(f'{member_id} has been unmuted {reason}')

    async def on_ready(self) -> None:
        pass

    @commands.command()
    async def mute(
        self,
        ctx: GuildContext,
        members: commands.Greedy[discord.Member],
        minutes: Optional[int] = None,
    ) -> None:
        role = await self.__get_mute_role(ctx.guild)

        if role is not None:
            if minutes is not None:
                now = pendulum.now()
                end_time = now.add(minutes=minutes)

            for member in members:
                try:
                    await member.add_roles(
                        role, reason=f'Muted by {ctx.message.author}'
                    )
                except discord.Forbidden:
                    await ctx.send_error(
                        f'Could not mute {member.mention}. Please make sure the '
                        '"Bothanasius" role is higher than the "bothanasius-mute" '
                        'role.',
                        title='Permissions incorrect',
                    )
                else:
                    await ctx.send_response(f'{member.mention} has been muted')

                    if minutes is None:
                        self.bot.delays.find_and_remove(
                            Unmute, guild_id=ctx.guild.id, member_id=member.id
                        )
                        await DelayedMute.delete_one(
                            guild_id=ctx.guild.id, member_id=member.id
                        )
                    else:
                        self.bot.delays.add(
                            Unmute(
                                guild_id=ctx.guild.id,
                                member_id=member.id,
                                created_at=now,
                                end_time=end_time,
                                callback=self.__run_action,
                            )
                        )
                        await DelayedMute.create_or_update(
                            guild=ctx.guild,
                            member=member,
                            end_time=end_time,
                            created_at=now,
                        )

    @commands.command()
    async def unmute(self, ctx: GuildContext, member: discord.Member) -> None:
        role = await self.__get_mute_role(ctx.guild)

        if role is not None:
            self.bot.delays.find_and_remove(
                Unmute, guild_id=ctx.guild.id, member_id=member.id
            )
            await DelayedMute.delete_one(guild_id=ctx.guild.id, member_id=member.id)

            try:
                await member.remove_roles(
                    role, reason=f'Unmuted by {ctx.message.author}'
                )
            except discord.Forbidden:
                await ctx.send_error(
                    f'Could not unmute {member.mention}. Please make sure the '
                    '"Bothanasius" role is higher than the "bothanasius-mute" role.',
                    title='Permissions incorrect',
                )
            else:
                await ctx.send_response(f'{member.mention} has been unmuted')

    @commands.command()
    async def warn(
        self, ctx: GuildContext, member: discord.Member, *, reason: Optional[str] = None
    ) -> None:
        await Warning.create(
            guild_id=ctx.guild.id,
            member_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            timestamp=pendulum.now(),
        )

    @commands.command()
    async def warnings(
        self, ctx: GuildContext, member: Optional[discord.Member] = None
    ) -> None:
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
                moderator = (
                    ctx.bot.get_user(warning.moderator_id) or warning.moderator_id
                )

                warning_title = underline(bold(f'ID: {warning.id}'))

                if warning.cleared_by is not None:
                    warning_title = strikethrough(warning_title)

                paginator.add_line(warning_title)
                paginator.add_line(
                    f'\t{bold("Date:")} {timestamp.strftime("%b %e %Y %H:%M:%S")}'
                )
                paginator.add_line(f'\t{bold("Moderator:")} {moderator}')
                paginator.add_line(
                    f'\t{bold("Reason:")} {warning.reason}',
                    empty=warning.cleared_by is None,
                )

                if warning.cleared_by is not None and warning.cleared_on is not None:
                    cleared_by = (
                        ctx.bot.get_user(int(warning.cleared_by)) or warning.cleared_by
                    )
                    paginator.add_line(f'\t{bold("Cleared by:")} {cleared_by}')
                    paginator.add_line(
                        f'\t{bold("Cleared on:")} '
                        f'{warning.cleared_on.strftime("%b %e %Y %H:%M:%S")}',
                        empty=True,
                    )

        page = None

        for page in paginator:
            await ctx.send_response(page, title=title)

        if page is None:
            if member is None:
                await ctx.send_response('No one has been warned')
            else:
                await ctx.send_response(f'{member} has not been warned')

    @commands.command()
    async def clearwarns(
        self, ctx: GuildContext, member: discord.Member, id: Optional[int] = None
    ) -> None:
        if id is None:
            await Warning.clear_all(ctx.guild, member, ctx.author.id)
            await ctx.send_response(f'Warnings cleared for {member}')
        else:
            await Warning.clear_one(ctx.guild, member, id, ctx.author.id)
            await ctx.send_response(f'Warning {id} cleared for {member}')

    @commands.command()
    async def kick(
        self, ctx: GuildContext, member: discord.Member, reason: Optional[str] = None
    ) -> None:
        await ctx.guild.kick(member, reason=reason)
        await ctx.send_response(f'{member.name} ({member}) has been kicked')

    @commands.command()
    async def ban(
        self, ctx: GuildContext, user: discord.User, reason: Optional[str] = None
    ) -> None:
        await ctx.guild.ban(user, reason=reason)
        await ctx.send_response(f'{user.name} ({user}) has been banned')

    @commands.command()
    async def invite(self, ctx: GuildContext, user: discord.User) -> None:
        invite = await ctx.channel.create_invite()
        await ctx.send(invite.url)


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Moderation(bot))
