from __future__ import annotations

from typing import Optional, Union

import discord
import logging
import pendulum

from discord.ext import commands
from botus_receptus.formatting import EmbedPaginator, underline, bold, strikethrough

from ..bothanasius import Bothanasius, DelayedAction
from ..db.admin import GuildPrefs, InviteArgumentParser
from ..db.mod import Warning
from ..context import Context, GuildContext
from ..checks import check_mod_only

log = logging.getLogger(__name__)


class Moderation(commands.Cog[Context]):
    def __init__(self, bot: Bothanasius) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return await check_mod_only(ctx)

    @commands.command()
    async def mute(
        self, ctx: GuildContext, member: discord.Member, minutes: Optional[int] = None
    ) -> None:
        role = (await ctx.guild_prefs).guild_mute_role

        if role is not None:
            if minutes is not None:
                now = pendulum.now()
                end_time = now.add(minutes=minutes)

            try:
                await member.add_roles(role, reason=f'Muted by {ctx.message.author}')
            except discord.Forbidden:
                log.error(
                    f'Could not mute {member.mention} in {ctx.guild.name} '
                    f'({ctx.guild.id})'
                )
                await ctx.send_error(
                    f'Could not mute {member.mention}. Please make sure the '
                    '`Bothanasius` role is higher than the `{role.name}` '
                    'role.',
                    title='Permissions incorrect',
                )
            else:
                await ctx.send_response(f'{member.mention} has been muted')

                if minutes is None:
                    await self.bot.remove_action('unmute', ctx.guild.id, member.id)
                else:
                    await self.bot.create_or_update_action(
                        end_time,
                        'unmute',
                        ctx.guild.id,
                        member.id,
                        moderator_id=ctx.author.id,
                        channel_id=ctx.channel.id,
                    )

    async def __unmute(
        self,
        guild: discord.Guild,
        member: discord.Member,
        channel: Optional[discord.TextChannel],
        reason: str,
    ) -> bool:
        prefs = await GuildPrefs.for_guild(guild)
        role = prefs.guild_mute_role

        if role is not None:
            await self.bot.remove_action('unmute', guild.id, member.id)

            try:
                await member.remove_roles(role, reason=reason)
            except discord.Forbidden:
                log.error(
                    f'Could not unmute {member.mention} in {guild.name} '
                    f'({guild.id})'
                )

                if channel:
                    await channel.send(
                        embed=discord.Embed(
                            title='Permissions incorrect',
                            color=discord.Color.red(),
                            description=f'Could not unmute {member.mention}. Please '
                            'make sure the `Bothanasius` role is higher than the '
                            f'`{role.name}` role.',
                        )
                    )

                return True
            else:
                if channel:
                    await channel.send(
                        embed=discord.Embed(
                            color=discord.Color.green(),
                            description=f'{member.mention} has been unmuted',
                        )
                    )

        return False

    @commands.command()
    async def unmute(self, ctx: GuildContext, member: discord.Member) -> None:
        ctx.has_error = await self.__unmute(
            ctx.guild, member, ctx.channel, f'Unmuted by {ctx.author}'
        )

    @commands.Cog.listener()
    async def on_unmute_action_complete(self, action: DelayedAction) -> None:
        guild_id, member_id = action.args  # type: int, int
        mod_id: int = action.kwargs['moderator_id']
        channel_id: int = action.kwargs['channel_id']

        guild, member = self.bot.get_guild_member(guild_id, member_id)

        if guild is None or member is None:
            return

        moderator: Optional[Union[discord.User, discord.Member]] = guild.get_member(
            mod_id
        )

        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except Exception:
                moderator_str = f'Moderator ID {mod_id}'
            else:
                moderator_str = f'{moderator} (ID: {mod_id})'
        else:
            moderator_str = f'{moderator} (ID: {mod_id})'

        channel = self.bot.get_channel(channel_id) or guild.system_channel

        await self.__unmute(
            guild,
            member,
            channel if isinstance(channel, discord.TextChannel) else None,
            f'Automatic unmute from mute on {action.created_at} by {moderator_str}',
        )

    async def __timein(
        self,
        guild: discord.Guild,
        member: discord.Member,
        channel: Optional[discord.TextChannel],
        reason: str,
    ) -> bool:
        prefs = await GuildPrefs.for_guild(guild)
        role = prefs.guild_time_out_role

        if role is not None:
            await self.bot.remove_action('time_in', guild.id, member.id)

            try:
                await member.remove_roles(role, reason=reason)
            except discord.Forbidden:
                log.error(
                    f'Could not time in {member.mention} in {guild.name} '
                    f'({guild.id})'
                )

                if channel:
                    await channel.send(
                        embed=discord.Embed(
                            title='Permissions incorrect',
                            color=discord.Color.red(),
                            description=f'Could not time in {member.mention}. Please '
                            'make sure the `Bothanasius` role is higher than the '
                            f'`{role.name}` role.',
                        )
                    )

                return True
            else:
                if channel:
                    await channel.send(
                        embed=discord.Embed(
                            color=discord.Color.green(),
                            description=f'Welcome back, {member.mention}',
                        )
                    )

        return False

    @commands.command()
    async def timeout(
        self,
        ctx: GuildContext,
        member: discord.Member,
        minutes: Optional[int] = None,
        *,
        reason: Optional[str] = None,
    ) -> None:
        role = (await ctx.guild_prefs).guild_time_out_role

        if role is not None:
            if minutes is not None:
                now = pendulum.now()
                end_time = now.add(minutes=minutes)

            try:
                await member.add_roles(
                    role, reason=f'Timed out by {ctx.message.author}'
                )
            except discord.Forbidden:
                log.error(
                    f'Could not time out {member.mention} in {ctx.guild.name} '
                    f'({ctx.guild.id})'
                )
                await ctx.send_error(
                    f'Could not time out {member.mention}. Please make sure the '
                    '`Bothanasius` role is higher than the `{role.name}` '
                    'role.',
                    title='Permissions incorrect',
                )
            else:
                if minutes is None:
                    await self.bot.remove_action('time_in', ctx.guild.id, member.id)
                else:
                    await self.bot.create_or_update_action(
                        end_time,
                        'time_in',
                        ctx.guild.id,
                        member.id,
                        moderator_id=ctx.author.id,
                        channel_id=ctx.channel.id,
                    )

    @commands.command(aliases=['untimeout'])
    async def timein(self, ctx: GuildContext, member: discord.Member) -> None:
        ctx.has_error = await self.__timein(
            ctx.guild, member, ctx.channel, f'Timed in by {ctx.author}'
        )

    @commands.Cog.listener()
    async def on_time_in_action_complete(self, action: DelayedAction) -> None:
        guild_id, member_id = action.args  # type: int, int
        mod_id: int = action.kwargs['moderator_id']
        channel_id: int = action.kwargs['channel_id']

        guild, member = self.bot.get_guild_member(guild_id, member_id)

        if guild is None or member is None:
            return

        moderator: Optional[Union[discord.User, discord.Member]] = guild.get_member(
            mod_id
        )

        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except Exception:
                moderator_str = f'Moderator ID {mod_id}'
            else:
                moderator_str = f'{moderator} (ID: {mod_id})'
        else:
            moderator_str = f'{moderator} (ID: {mod_id})'

        channel = self.bot.get_channel(channel_id) or guild.system_channel

        await self.__unmute(
            guild,
            member,
            channel if isinstance(channel, discord.TextChannel) else None,
            f'Automatic time in from time out on {action.created_at} by '
            f'{moderator_str}',
        )

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
    async def invite(
        self,
        ctx: GuildContext,
        user: Optional[discord.User] = None,
        *,
        options: str = '',
    ) -> None:
        """Create an invite

        The following options are valid:

        `--max-age`: How long until an invite expires (0 for never; in minutes or
                     formatted string)
        `--max-uses`: Maximum number of uses (0 for unlimited)
        `--temporary` / `--not-temporary`: Grant temporary membership
        `--unique` / `--not-unique`: Create a unique invite URL every time

        Max age formating:

        `--max-age` accepts a string containing multiple sets of numbers followed by a
        unit identifier. Sets can have spaces between them. The unit identifiers are as
        follows:

        s - seconds
        m - minutes
        h - hours
        d - days
        w - weeks
        y - years

        Examples:

        1m30s - 1 minute and 30 seconds
        1d 5h 42s - one day, 5 hours, and 42 seconds
        """

        parsed = await InviteArgumentParser.parse(
            ctx, (await ctx.guild_prefs).invite_prefs, options
        )

        if parsed is not None:
            invite = await ctx.channel.create_invite(
                reason=f'Requested by {ctx.author}', **parsed
            )
            if user is None:
                await ctx.send(invite.url)
            else:
                await user.send(invite.url)


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Moderation(bot))
