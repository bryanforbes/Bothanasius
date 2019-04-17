from __future__ import annotations

from typing import Any, Union, Callable, Coroutine, TypeVar, cast

import discord
from discord.ext import commands

from .context import Context

CoroType = Callable[..., Coroutine[Any, Any, Any]]
F = TypeVar('F', bound=Union[CoroType, commands.Command[Any]])


def check_guild_only(ctx: Context) -> bool:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            'This command cannot be used in private messages.'
        )

    return True


async def check_admin_only(ctx: Context) -> bool:
    if not check_guild_only(ctx):
        return False

    assert ctx.guild is not None

    if ctx.guild.owner == ctx.author:
        return True

    prefs = await ctx.guild_prefs
    author = cast(discord.Member, ctx.author)
    role_ids = {role.id for role in author.roles}
    admin_ids = set(prefs.admin_roles) if prefs.admin_roles is not None else set()

    return bool(role_ids & admin_ids)


async def check_mod_only(ctx: Context) -> bool:
    if not check_guild_only(ctx):
        return False

    assert ctx.guild is not None

    if ctx.guild.owner == ctx.author:
        return True

    prefs = await ctx.guild_prefs
    author = cast(discord.Member, ctx.author)
    role_ids = {role.id for role in author.roles}
    mod_ids = set(
        (prefs.admin_roles if prefs.admin_roles else [])
        + (prefs.mod_roles if prefs.mod_roles else [])
    )

    return bool(role_ids & mod_ids)


guild_only = commands.check(check_guild_only)
admin_only = commands.check(check_admin_only)
mod_only = commands.check(check_mod_only)
