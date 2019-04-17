from __future__ import annotations

from typing import Optional

import attr
import logging
import discord

from discord.ext import commands
from botus_receptus import formatting

from ..bothanasius import Bothanasius
from ..context import Context, GuildContext
from ..db.admin import InviteArgumentParser
from ..checks import check_admin_only

log = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True)
class InviteParsed(object):
    max_age: int = attr.ib(init=False)
    max_uses: int = attr.ib(init=False)
    temporary: int = attr.ib(init=False)
    unique: bool = attr.ib(init=False)


class Administration(commands.Cog[Context]):
    def __init__(self, bot: Bothanasius) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return await check_admin_only(ctx)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: Context) -> None:
        if not ctx.has_error:
            await ctx.message.delete()

    @commands.group()
    async def settings(self, ctx: GuildContext) -> None:
        if ctx.invoked_subcommand is None:
            prefs = await ctx.guild_prefs
            mute_role = prefs.guild_mute_role

            await ctx.send_embed(
                '',
                title='Bothanasius Settings',
                fields=[
                    {
                        'name': 'Prefix',
                        'value': formatting.inline_code(prefs.prefix)
                        if prefs.prefix is not None
                        else '\U0001f6ab',
                        'inline': True,
                    },
                    {
                        'name': 'Admin Roles',
                        'value': '\n'.join(
                            map(lambda role: role.name, prefs.guild_admin_roles)
                        )
                        or '\U0001f6ab',
                        'inline': True,
                    },
                    {
                        'name': 'Mod Roles',
                        'value': '\n'.join(
                            map(lambda role: role.name, prefs.guild_mod_roles)
                        )
                        or '\U0001f6ab',
                        'inline': True,
                    },
                    {
                        'name': 'Mute Role',
                        'value': mute_role.name
                        if mute_role is not None
                        else '\U0001f6ab',
                        'inline': True,
                    },
                ],
            )

    @settings.command()
    async def prefix(self, ctx: GuildContext, prefix: str) -> None:
        prefs = await ctx.guild_prefs
        await prefs.update(prefix=prefix).apply()
        self.bot.prefix_map[ctx.guild.id] = prefix
        await ctx.send_response(f'Prefix set to {formatting.inline_code(prefix)}')

    @settings.command()
    async def invites(self, ctx: GuildContext, *, options: str) -> None:
        """Default invite settings

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

        prefs = await ctx.guild_prefs
        parsed = await InviteArgumentParser.parse(ctx, prefs.invite_prefs, options)

        if parsed is not None:
            await prefs.update(**parsed).apply()

    @settings.command()
    async def muterole(
        self, ctx: GuildContext, role: Optional[discord.Role] = None
    ) -> None:
        prefs = await ctx.guild_prefs
        await prefs.set_mute_role(role)

        if role is not None:
            await ctx.send_response(f'Mute role set to `{role.name}`')
        else:
            await ctx.send_response('Mute role set to `Muted`')

    @settings.command()
    async def addadminrole(self, ctx: GuildContext, role: discord.Role) -> None:
        prefs = await ctx.guild_prefs
        await prefs.add_admin_role(role)
        await ctx.send_response(f'Added {role.name} to admin roles')

    @settings.command()
    async def deladminrole(self, ctx: GuildContext, role: discord.Role) -> None:
        prefs = await ctx.guild_prefs
        await prefs.remove_admin_role(role)
        await ctx.send_response(f'Deleted {role.name} from admin roles')

    @settings.command()
    async def addmodrole(self, ctx: GuildContext, role: discord.Role) -> None:
        prefs = await ctx.guild_prefs
        await prefs.add_mod_role(role)
        await ctx.send_response(f'Added {role.name} to mod roles')

    @settings.command()
    async def delmodrole(self, ctx: GuildContext, role: discord.Role) -> None:
        prefs = await ctx.guild_prefs
        await prefs.remove_mod_role(role)
        await ctx.send_response(f'Deleted {role.name} from mod roles')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Administration(bot))
