from __future__ import annotations

import discord
import datetime

from typing import List, Tuple
from sqlalchemy.dialects.postgresql import insert
from . import db, Snowflake, Base


class DelayedMute(Base):
    __tablename__ = 'delayed_mutes'

    guild_id = db.Column(Snowflake(), primary_key=True)
    member_id = db.Column(Snowflake(), primary_key=True)
    end_time = db.Column(db.DateTime())
    created_at = db.Column(db.DateTime())

    @property
    def seconds(self) -> float:
        return (self.end_time - self.created_at).total_seconds()

    @staticmethod
    async def delete_one(*, guild_id: int, member_id: int) -> None:
        await DelayedMute.delete \
            .where(db.and_(DelayedMute.guild_id == guild_id, DelayedMute.member_id == member_id)) \
            .gino.status()

    @staticmethod
    async def delete_prior_to(date: datetime.datetime) -> None:
        await DelayedMute.delete \
            .where(DelayedMute.end_time <= date) \
            .gino.status()

    @staticmethod
    async def get_all_ascending() -> List[DelayedMute]:  # noqa: F821
        return await DelayedMute.query \
            .order_by(db.asc(DelayedMute.end_time)) \
            .gino.all()

    @staticmethod
    async def create_or_update(*, guild: discord.Guild, member: discord.Member,
                               end_time: datetime.datetime, created_at: datetime.datetime) -> None:
        stmt = insert(DelayedMute).values(guild_id=guild.id,
                                          member_id=member.id,
                                          end_time=end_time,
                                          created_at=created_at)
        stmt = stmt.on_conflict_do_update(index_elements=['guild_id', 'member_id'],
                                          set_=dict(end_time=stmt.excluded.end_time))
        await db.scalar(stmt)


class Warning(Base):
    __tablename__ = 'warnings'

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    guild_id = db.Column(Snowflake())
    member_id = db.Column(Snowflake())
    moderator_id = db.Column(Snowflake())
    reason = db.Column(db.String(), nullable=True)
    timestamp = db.Column(db.DateTime())
    cleared_on = db.Column(db.DateTime(), nullable=True)
    cleared_by = db.Column(Snowflake(), nullable=True)

    _idx1 = db.Index('warnings_guild_idx', 'guild_id')
    _idx2 = db.Index('warnings_guild_member_idx', 'guild_id', 'member_id')

    @staticmethod
    async def get_guild_counts(guild: discord.Guild) -> List[Tuple[int, int, int]]:
        return await db.all(db.select([Warning.member_id,
                                       db.func.sum(db.cast(db.case([(Warning.cleared_on.is_(None), '1')],
                                                                   else_='0'), db.Integer())),
                                       db.func.count(Warning.member_id)])
                            .where(Warning.guild_id == guild.id)
                            .group_by(Warning.member_id))

    @staticmethod
    async def get_for_member(guild: discord.Guild, member: discord.Member) -> List[Warning]:  # noqa: F821
        return await Warning.query \
            .where(db.and_(Warning.guild_id == guild.id, Warning.member_id == member.id)) \
            .order_by(Warning.timestamp) \
            .gino.all()

    @staticmethod
    async def clear_all(guild: discord.Guild, member: discord.Member, cleared_by: int) -> None:
        await Warning.update \
            .values(cleared_on=datetime.datetime.now(),
                    cleared_by=cleared_by) \
            .where(db.and_(Warning.guild_id == guild.id,
                           Warning.member_id == member.id,
                           Warning.cleared_on.is_(None))) \
            .gino.status()

    @staticmethod
    async def clear_one(guild: discord.Guild, member: discord.Member, id: int, cleared_by: int) -> None:
        await Warning.update \
            .values(cleared_on=datetime.datetime.now(),
                    cleared_by=cleared_by) \
            .where(db.and_(Warning.guild_id == guild.id,
                           Warning.member_id == member.id,
                           Warning.id == id,
                           Warning.cleared_on.is_(None))) \
            .gino.status()
