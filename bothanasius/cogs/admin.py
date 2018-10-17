from __future__ import annotations

from typing import Any, Iterable, cast

import attr
import logging
import discord

from discord.ext import commands
from botus_receptus import formatting

from ..bothanasius import Bothanasius
from ..context import Context, GuildContext
from ..db.admin import GuildPrefs

log = logging.getLogger(__name__)


@attr.s(slots=True, auto_attribs=True)
class Administration(object):
    bot: Bothanasius
    __weakref__: Any = attr.ib(init=False, hash=False, repr=False, cmp=False)

    async def on_command_completion(self, ctx: Context) -> None:
        if not ctx.has_error:
            await ctx.message.delete()

    async def __local_check(self, ctx: Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.guild.owner != ctx.author and not await ctx.has_admin_role():
            return False

        return True

    @commands.command()
    async def prefix(self, ctx: GuildContext, prefix: str) -> None:
        await self.bot.set_prefix(ctx, ctx.guild, prefix)
        await ctx.send_response(f'Prefix set to {formatting.inline_code(prefix)}')

    @commands.command()
    async def addadminrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await GuildPrefs.add_admin_role(ctx.guild, role)
        await ctx.send_response(f'Added {role.name} to admin roles')

    @commands.command()
    async def deladminrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await GuildPrefs.remove_admin_role(ctx.guild, role)
        await ctx.send_response(f'Deleted {role.name} from admin roles')

    @commands.command()
    async def adminroles(self, ctx: GuildContext) -> None:
        prefs = await GuildPrefs.get(ctx.guild.id)

        if prefs:
            roles: Iterable[discord.Role] = filter(lambda role: role.id in cast(GuildPrefs, prefs).admin_roles,
                                                   ctx.guild.roles)
        else:
            roles = []

        await ctx.send_response('\n'.join([role.name for role in roles]), title='Administration Roles')

    @commands.command()
    async def addmodrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await GuildPrefs.add_mod_role(ctx.guild, role)
        await ctx.send_response(f'Added {role.name} to mod roles')

    @commands.command()
    async def delmodrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await GuildPrefs.remove_mod_role(ctx.guild, role)
        await ctx.send_response(f'Deleted {role.name} from mod roles')

    @commands.command()
    async def modroles(self, ctx: GuildContext) -> None:
        prefs = await GuildPrefs.get(ctx.guild.id)

        if prefs:
            roles: Iterable[discord.Role] = filter(lambda role: role.id in cast(GuildPrefs, prefs).mod_roles,
                                                   ctx.guild.roles)
        else:
            roles = []

        await ctx.send_response('\n'.join([role.name for role in roles]), title='Moderation Roles')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Administration(bot))
