from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union
from botus_receptus import PaginatedContext, EmbedContext
from botus_receptus.context import (
    FooterData,
    AuthorData,
    FieldData,
    GuildContext as BaseGuildContext,
)
from datetime import datetime

from .db.admin import GuildPrefs

import discord

if TYPE_CHECKING:
    from .bothanasius import Bothanasius


class Context(PaginatedContext, EmbedContext):
    bot: Bothanasius
    has_error: bool = False

    async def send_error(
        self,
        description: str,
        *,
        title: Optional[str] = None,
        footer: Optional[Union[str, FooterData]] = None,
        thumbnail: Optional[str] = None,
        author: Optional[Union[str, AuthorData]] = None,
        image: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        fields: Optional[List[FieldData]] = None,
        tts: bool = False,
        file: Optional[discord.File] = None,
        files: Optional[List[discord.File]] = None,
        delete_after: Optional[float] = None,
        nonce: Optional[int] = None,
    ) -> discord.Message:
        self.has_error = True
        return await self.send_embed(
            description,
            color=discord.Color.red(),
            title=title,
            footer=footer,
            thumbnail=thumbnail,
            author=author,
            image=image,
            timestamp=timestamp,
            fields=fields,
            tts=tts,
            file=file,
            files=files,
            delete_after=delete_after,
            nonce=nonce,
        )

    async def send_response(
        self,
        description: str,
        *,
        title: Optional[str] = None,
        color: Optional[Union[discord.Color, int]] = None,
        footer: Optional[Union[str, FooterData]] = None,
        thumbnail: Optional[str] = None,
        author: Optional[Union[str, AuthorData]] = None,
        image: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        fields: Optional[List[FieldData]] = None,
        tts: bool = False,
        file: Optional[discord.File] = None,
        files: Optional[List[discord.File]] = None,
        delete_after: Optional[float] = None,
        nonce: Optional[int] = None,
    ) -> discord.Message:
        return await self.send_embed(
            description,
            color=color if color is not None else discord.Color.green(),
            title=title,
            footer=footer,
            thumbnail=thumbnail,
            author=author,
            image=image,
            timestamp=timestamp,
            fields=fields,
            tts=tts,
            file=file,
            files=files,
            delete_after=delete_after,
            nonce=nonce,
        )

    @discord.utils.cached_property
    async def guild_prefs(self) -> GuildPrefs:
        assert self.guild is not None

        return await GuildPrefs.for_guild(self.guild)


class GuildContext(Context, BaseGuildContext):
    pass
