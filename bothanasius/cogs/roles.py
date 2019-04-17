from __future__ import annotations

from typing import Optional

import discord

from asyncpg import UniqueViolationError
from discord.ext import commands
from botus_receptus.formatting import EmbedPaginator

from ..bothanasius import Bothanasius
from ..checks import check_guild_only, admin_only
from ..context import Context, GuildContext
from ..db.roles import SelfRole


class NotAssignable(commands.CommandError):
    def __init__(self, name: str) -> None:
        super().__init__(message=f'The role \'{name}\' is not assignable')


class Roles(commands.Cog[Context]):
    def __init__(self, bot: Bothanasius) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return check_guild_only(ctx)

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, NotAssignable):
            await ctx.send_error(error.args[0])

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await SelfRole.delete_one(role.guild, role)

    async def __get_self_role(
        self, ctx: GuildContext, role: discord.Role
    ) -> discord.Role:
        if (
            await SelfRole.get(
                {SelfRole.guild_id.name: ctx.guild.id, SelfRole.role_id.name: role.id}
            )
            is None
        ):
            raise NotAssignable(role.name)

        return role

    @commands.command()
    async def iam(self, ctx: GuildContext, *, role: discord.Role) -> None:
        role_obj = await self.__get_self_role(ctx, role)

        await ctx.author.add_roles(role_obj, reason='Self-assigned role')

    @commands.command(aliases=['iamn'])
    async def iamnot(self, ctx: GuildContext, *, role: discord.Role) -> None:
        role_obj = await self.__get_self_role(ctx, role)

        await ctx.author.remove_roles(role_obj, reason='Self-unassigned role')

    @commands.command()
    async def roles(self, ctx: GuildContext) -> None:
        paginator = EmbedPaginator()

        async for record in SelfRole.get_for_guild(ctx.guild):
            role = ctx.guild.get_role(record.role_id)

            if role is None:
                continue

            paginator.add_line(role.name)

        page: Optional[str] = None
        for page in paginator:
            await ctx.send_response(page, title='Self-assignable roles')

        if page is None:
            await ctx.send_response(
                'No self-assignable roles', title='Self-assignable roles'
            )

    @admin_only
    @commands.command()
    async def addselfrole(self, ctx: GuildContext, *, role: discord.Role) -> None:
        try:
            await SelfRole.create(guild_id=ctx.guild.id, role_id=role.id)
        except UniqueViolationError:
            await ctx.send_response(f'\'{role.name}\' is already self-assignable')
        else:
            await ctx.send_response(f'\'{role.name}\' is now self-assignable')

    @admin_only
    @commands.command()
    async def delselfrole(self, ctx: GuildContext, *, role: discord.Role) -> None:
        await SelfRole.delete_one(ctx.guild, role)
        await ctx.send_response(f'\'{role.name}\' is no longer self-assignable')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Roles(bot))
