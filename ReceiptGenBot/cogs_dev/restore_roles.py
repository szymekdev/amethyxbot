import os
import lightbulb
import hikari
from receiptgen import receiptgen, database, utils

plugin = lightbulb.Plugin("restore_roles")


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="restore_roles", description="sends email to guild users")
@lightbulb.implements(lightbulb.SlashCommand)
async def restore_roles(ctx: lightbulb.Context):
    await ctx.respond("giving back user access")
    members = await ctx.bot.rest.fetch_members(guild=ctx.guild_id)

    for member in members:
        db = database.GuildMemberAPI(guild_id=str(ctx.guild_id), member_id=str(member.id))
        guild_member = await db.get_guild_member()
        role_id = utils.get_config()["roles"]["access"]

        if guild_member.get("error", False):
            continue

        filtered_dict = {key: guild_member[key] for key in ['emulator_access', 'paper_generator_access', 'has_access'] if key in guild_member}

        if guild_member["emulator_access"] or guild_member["paper_generator_access"] or guild_member["has_access"]:

            try:
                await member.add_role(role=role_id)
                await ctx.bot.rest.create_message(content=filtered_dict, channel=ctx.channel_id)
                await ctx.bot.rest.create_message(content=f"role added to {member.mention}", channel=ctx.channel_id)

            except Exception as e:
                await ctx.bot.rest.create_message(content=e, channel=ctx.channel_id)

        elif not all([guild_member["emulator_access"], guild_member["paper_generator_access"], guild_member["has_access"]]):
            try:
                await member.remove_role(role=role_id)
                await ctx.bot.rest.create_message(content=filtered_dict, channel=ctx.channel_id)
                await ctx.bot.rest.create_message(content=f"role removed from {member.mention}", channel=ctx.channel_id)

            except Exception as e:
                await ctx.bot.rest.create_message(content=e, channel=ctx.channel_id)



def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)