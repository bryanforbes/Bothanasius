from __future__ import annotations

import discord
import pendulum

from typing import List, Tuple
from botus_receptus.gino import Snowflake

from .base import db, Base
from ..db import DateTime


class Warning(Base):
    __tablename__ = 'warnings'

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    guild_id = db.Column(Snowflake(), nullable=False)
    member_id = db.Column(Snowflake(), nullable=False)
    moderator_id = db.Column(Snowflake(), nullable=False)
    reason = db.Column(db.String())
    timestamp = db.Column(DateTime(), nullable=False)
    cleared_on = db.Column(DateTime())
    cleared_by = db.Column(Snowflake())

    _idx1 = db.Index('warnings_guild_idx', 'guild_id')
    _idx2 = db.Index('warnings_guild_member_idx', 'guild_id', 'member_id')

    @staticmethod
    async def get_guild_counts(guild: discord.Guild) -> List[Tuple[int, int, int]]:
        return await db.all(
            db.select(
                [
                    Warning.member_id,
                    db.func.sum(
                        db.cast(
                            db.case([(Warning.cleared_on.is_(None), '1')], else_='0'),
                            db.Integer(),
                        )
                    ),
                    db.func.count(Warning.member_id),
                ]
            )
            .where(Warning.guild_id == guild.id)
            .group_by(Warning.member_id)
        )

    @staticmethod
    async def get_for_member(
        guild: discord.Guild, member: discord.Member
    ) -> List[Warning]:
        return (
            await Warning.query.where(
                db.and_(Warning.guild_id == guild.id, Warning.member_id == member.id)
            )
            .order_by(Warning.timestamp)
            .gino.all()
        )

    @staticmethod
    async def clear_all(
        guild: discord.Guild, member: discord.Member, cleared_by: int
    ) -> None:
        await Warning.update.values(
            cleared_on=pendulum.now(), cleared_by=cleared_by
        ).where(
            db.and_(
                Warning.guild_id == guild.id,
                Warning.member_id == member.id,
                Warning.cleared_on.is_(None),
            )
        ).gino.status()

    @staticmethod
    async def clear_one(
        guild: discord.Guild, member: discord.Member, id: int, cleared_by: int
    ) -> None:
        await Warning.update.values(
            cleared_on=pendulum.now(), cleared_by=cleared_by
        ).where(
            db.and_(
                Warning.guild_id == guild.id,
                Warning.member_id == member.id,
                Warning.id == id,
                Warning.cleared_on.is_(None),
            )
        ).gino.status()
