from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union, cast
from botus_receptus import PaginatedContext, EmbedContext
from botus_receptus.context import FooterData, AuthorData, FieldData
from datetime import datetime

from .db.admin import GuildPrefs

import discord

if TYPE_CHECKING:
    from .bothanasius import Bothanasius  # noqa: F401


class Context(PaginatedContext, EmbedContext):
    bot: 'Bothanasius'
    has_error: bool = False

    async def send_error(self, description: str, *,
                         title: Optional[str] = None,
                         footer: Optional[Union[str, FooterData]] = None,
                         thumbnail: Optional[str] = None,
                         author: Optional[Union[str, AuthorData]] = None,
                         image: Optional[str] = None,
                         timestamp: Optional[datetime] = None,
                         fields: Optional[List[FieldData]] = None,
                         tts: bool = False, file: Optional[discord.File] = None,
                         files: Optional[List[discord.File]] = None, delete_after: Optional[float] = None,
                         nonce: Optional[int] = None) -> discord.Message:
        self.has_error = True
        return await self.send_embed(description, color=discord.Color.red(), title=title, footer=footer,
                                     thumbnail=thumbnail, author=author, image=image, timestamp=timestamp,
                                     fields=fields, tts=tts, file=file, files=files, delete_after=delete_after,
                                     nonce=nonce)

    async def send_response(self, description: str, *,
                            title: Optional[str] = None,
                            color: Optional[Union[discord.Color, int]] = discord.Color.green(),
                            footer: Optional[Union[str, FooterData]] = None,
                            thumbnail: Optional[str] = None,
                            author: Optional[Union[str, AuthorData]] = None,
                            image: Optional[str] = None,
                            timestamp: Optional[datetime] = None,
                            fields: Optional[List[FieldData]] = None,
                            tts: bool = False, file: Optional[discord.File] = None,
                            files: Optional[List[discord.File]] = None, delete_after: Optional[float] = None,
                            nonce: Optional[int] = None) -> discord.Message:
        return await self.send_embed(description, color=color, title=title, footer=footer,
                                     thumbnail=thumbnail, author=author, image=image, timestamp=timestamp,
                                     fields=fields, tts=tts, file=file, files=files, delete_after=delete_after,
                                     nonce=nonce)

    async def has_admin_role(self) -> bool:
        if self.guild is None:
            return False

        role_ids = [str(role.id) for role in cast(discord.Member, self.author).roles]

        return await GuildPrefs.query \
            .where(GuildPrefs.guild_id == self.guild.id) \
            .where(GuildPrefs.admin_roles.overlap(role_ids)) \
            .gino.first() is not None

    async def has_mod_role(self) -> bool:
        if self.guild is None:
            return False

        role_ids = [str(role.id) for role in cast(discord.Member, self.author).roles]

        return await GuildPrefs.query \
            .where(GuildPrefs.guild_id == self.guild.id) \
            .where((GuildPrefs.admin_roles + GuildPrefs.mod_roles).overlap(role_ids)) \
            .gino.first() is not None


class GuildContext(Context):
    author: discord.Member
    guild: discord.Guild
