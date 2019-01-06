from __future__ import annotations

from typing import List

import attr
import discord

from asyncpg import UniqueViolationError
from discord.ext import commands
from botus_receptus.abc import OnMemberUpdate, OnGuildRoleDelete
from botus_receptus.formatting import EmbedPaginator
from botus_receptus.gino import db

from ..db import Ltree
from ..db.roles import LinkedRole, SelfRole
from ..bothanasius import Bothanasius
from ..context import Context, GuildContext


class NotAModerator(commands.CommandError):
    def __init__(self) -> None:
        super().__init__(message=f'You must be a moderator to use this command')


class NotAssignable(commands.CommandError):
    def __init__(self, name: str) -> None:
        super().__init__(message=f'The role \'{name}\' is not assignable')


async def is_moderator(ctx: GuildContext) -> bool:
    if ctx.guild.owner != ctx.author and not await ctx.has_mod_role():
        raise NotAModerator()

    return True


@attr.s(slots=True, auto_attribs=True)
class Roles(OnMemberUpdate, OnGuildRoleDelete):
    bot: Bothanasius

    id_converter: commands.RoleConverter = attr.ib(
        init=False, default=attr.Factory(commands.RoleConverter)
    )

    async def __local_check(self, ctx: Context) -> bool:
        if ctx.guild is None:
            return False

        return True

    async def __error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, NotAssignable) or isinstance(error, NotAModerator):
            await ctx.send_error(error.args[0])
        elif isinstance(
            error, (commands.BadArgument, commands.MissingRequiredArgument)
        ):
            pages = await ctx.bot.formatter.format_help_for(ctx, ctx.command)

            for page in pages:
                await ctx.send(page)
        else:
            raise error

    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        print('on_member_update')
        if before.roles == after.roles:
            return

        before_role_set = set(before.roles)
        after_role_set = set(after.roles)

        new_roles = set(after.roles)

        added_role_ids = [
            str(f'*.{role.id}') for role in after_role_set - before_role_set
        ]
        # removed_role_ids = [str(role.id) for role in before_role_set - after_role_set]

        linked_roles: List[LinkedRole] = await LinkedRole.query.where(
            LinkedRole.guild_id == after.guild.id
        ).where(LinkedRole.path.lquery(added_role_ids)).gino.all()

        for linked_role in linked_roles:
            path = linked_role.path.path[0:-1]
            parent_ids = [int(id) for id in path]
            roles = filter(
                lambda r: r.id in parent_ids and r not in new_roles, after.guild.roles
            )
            for role in roles:
                new_roles.add(role)

            # role_records = await get_linked_roles(
            #     conn,
            #     str(after.guild.id),
            #     removed_role_ids,
            #     where=['guild_id = $1', 'role_id = ANY($2)'],
            # )

            # for role_record in role_records:
            #     sibling_records = await get_linked_roles(
            #         conn,
            #         str(after.guild.id),
            #         role_record['parent_role_id'],
            #         where=['guild_id = $1', 'parent_role_id = $2'],
            #     )

            #     sibling_roles = set(
            #         cast(
            #             Iterable[discord.Role],
            #             filter(
            #                 lambda x: x is not None and x in after.roles,
            #                 [
            #                     discord.utils.get(
            #                         after.guild.roles, id=int(sibling_record['role_id'])  # noqa
            #                     )
            #                     for sibling_record in sibling_records
            #                 ],
            #             ),
            #         )
            #     )

            #     parent_role = discord.utils.get(
            #         after.guild.roles, id=int(role_record['parent_role_id'])
            #     )
            #     if (
            #         new_roles.isdisjoint(sibling_roles)
            #         and parent_role is not None
            #         and parent_role in new_roles
            #     ):
            #         new_roles.remove(parent_role)

        if new_roles != after_role_set:
            await after.edit(reason='Linked roles', roles=list(new_roles))

    async def on_guild_role_delete(self, role: discord.Role) -> None:
        async with db.transaction():
            await SelfRole.delete_one(role.guild, role)
            # TODO: delete child links
            await LinkedRole.delete.where(LinkedRole.guild_id == role.guild.id).where(
                LinkedRole.role_id == role.id
            ).gino.status()

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

    @commands.check(is_moderator)
    @commands.has_permissions(manage_roles=True)
    @commands.command()
    async def linkrole(
        self, ctx: GuildContext, role: discord.Role, parent: discord.Role
    ) -> None:
        parent_record = await LinkedRole.get(
            {LinkedRole.guild_id.name: ctx.guild.id, LinkedRole.role_id.name: parent.id}
        )

        if parent_record is None:
            parent_record = await LinkedRole.create(
                guild_id=ctx.guild.id, role_id=parent.id, path=Ltree(str(parent.id))
            )

        await LinkedRole.create(
            guild_id=ctx.guild.id,
            role_id=role.id,
            path=parent_record.path + str(role.id),
        )

        await ctx.send_response('Roles linked')

    @commands.check(is_moderator)
    @commands.has_permissions(manage_roles=True)
    @commands.command()
    async def unlinkrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await LinkedRole.delete.where(LinkedRole.guild_id == ctx.guild.id).where(
            LinkedRole.role_id == role.id
        ).gino.status()
        await ctx.send_response('Role unlinked')

    @commands.check(is_moderator)
    @commands.command(aliases=['asr'])
    async def addselfrole(self, ctx: GuildContext, *, role: discord.Role) -> None:
        try:
            await SelfRole.create(guild_id=ctx.guild.id, role_id=role.id)
        except UniqueViolationError:
            await ctx.send_response(f'\'{role.name}\' is already self-assignable')
        else:
            await ctx.send_response(f'\'{role.name}\' is now self-assignable')

    @commands.check(is_moderator)
    @commands.command(aliases=['rmsr'])
    async def removeselfrole(self, ctx: GuildContext, *, role: discord.Role) -> None:
        await SelfRole.delete_one(ctx.guild, role)
        await ctx.send_response(f'\'{role.name}\' is no longer self-assignable')

    @commands.check(is_moderator)
    @commands.command(aliases=['lssr'])
    async def listselfroles(self, ctx: GuildContext) -> None:
        role_records = await SelfRole.get_for_guild(ctx.guild)

        paginator = EmbedPaginator()

        for record in role_records:
            role = ctx.guild.get_role(record.role_id)

            if role is None:
                continue

            paginator.add_line(role.name)

        for page in paginator:
            await ctx.send_response(page, title='Self-assignable roles')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(Roles(bot))
