from __future__ import annotations

import logging

from discord.ext import commands

from ..context import Context
from ..bothanasius import Bothanasius

log = logging.getLogger(__name__)


class Meta(commands.Cog[Context]):
    def __init__(self, bot: Bothanasius) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.command(name='reload', hidden=True)
    async def _reload(self, ctx: Context, module: str) -> None:
        try:
            self.bot.reload_extension(f'bothanasius.cogs.{module}')
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
            log.exception('Failed to load extension %s.', module)


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Meta(bot))
