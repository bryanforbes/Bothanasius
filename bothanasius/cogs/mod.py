from typing import Any, Optional

import attr

import discord
from discord.ext import commands
from ..bothanasius import Bothanasius  # noqa: F401
from botus_receptus.db import Context


@attr.s(slots=True, auto_attribs=True)
class Moderation(object):
    bot: Bothanasius
    __weakref__: Any = attr.ib(init=False, hash=False, repr=False, cmp=False)

    @commands.command()
    async def mute(self, ctx: Context, member: Optional[discord.Member] = None) -> None:
        await ctx.send('Hi!')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Moderation(bot))
