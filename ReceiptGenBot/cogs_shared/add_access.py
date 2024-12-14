import datetime
import hikari
import lightbulb
from receiptgen import database, utils

plugin = lightbulb.Plugin("add-access")

@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.option(name="member", description="User to add access to", required=True, type=hikari.Member)
@lightbulb.option(name="days", description="Amount of days", required=False, type=int)
@lightbulb.option(name="forever", description="Forever access", required=False, type=bool)
@lightbulb.command(name="add_access", description="Add User Access")
@lightbulb.implements(lightbulb.SlashCommand)
async def add_access(ctx: lightbulb.Context):
    days = getattr(ctx.options, "days", None)
    forever = getattr(ctx.options, "forever", None)
    member = getattr(ctx.options, "member")

    db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=member.id)

    response = await ctx.respond("Adding access to member...", flags=hikari.MessageFlag.EPHEMERAL)

    if days and forever is None:
        result = await db.update_guild_member(days=days)

    elif forever and days is None:
        result = await db.update_guild_member(days=99999)


    else:
        await response.edit("Pick one Option")
        return

    if not result.get("error", False):
        await response.edit("Successfully added access to member")

    else:
        await response.edit(result["error"])

def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)