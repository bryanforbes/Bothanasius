from __future__ import annotations

from typing import List

import discord

from discord.ext import commands

from ..bothanasius import Bothanasius
from ..checks import check_guild_only, admin_only
from ..context import Context, GuildContext
from ..db.linked_roles import LinkedRole
from ..db import Ltree


class LinkedRoles(commands.Cog[Context]):
    def __init__(self, bot: Bothanasius) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return check_guild_only(ctx)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await LinkedRole.delete.where(LinkedRole.guild_id == role.guild.id).where(
            LinkedRole.role_id == role.id
        ).gino.status()

    @commands.Cog.listener()
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

    @admin_only
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

    @admin_only
    @commands.command()
    async def unlinkrole(self, ctx: GuildContext, role: discord.Role) -> None:
        await LinkedRole.delete.where(LinkedRole.guild_id == ctx.guild.id).where(
            LinkedRole.role_id == role.id
        ).gino.status()
        await ctx.send_response('Role unlinked')


def setup(bot: Bothanasius) -> None:
    bot.add_cog(LinkedRoles(bot))
