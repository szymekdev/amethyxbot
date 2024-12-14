import datetime
import hikari
import lightbulb
import miru
from miru.ext import menu
from receiptgen import database, utils

plugin = lightbulb.Plugin("get-access")


@plugin.command
@lightbulb.decorators.app_command_permissions(dm_enabled=False)
@lightbulb.command(name="access", description="Your Access Information")
@lightbulb.implements(lightbulb.SlashCommand)
async def get_access(ctx: lightbulb.Context):
    db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=ctx.author.id)
    data = await db.get_guild_member()

    access = data.get("has_access", False)
    access_end = data.get("access_end")

    if access_end:
        try:
            access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            try:
                access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:

                access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S")

    embed = hikari.Embed(
        title="Access Info",
        color=utils.get_config()["color"],
        timestamp=datetime.datetime.now().astimezone()
    ).add_field("Till", "`None`", inline=True) \
        .add_field("Ends", "`None`", inline=True) \
        .add_field("Active", "`False`", inline=True) \
        .set_footer(text=plugin.bot.get_me().username)

    if not access and access_end:
        embed = hikari.Embed(
            title="Access Info",
            timestamp=datetime.datetime.now().astimezone()
           ).add_field("Till", "`None`", inline=True) \
            .add_field("Ended", f"<t:{int(access_end.timestamp())}:R>", inline=True) \
            .add_field("Active", "`False`", inline=True) \
            .set_footer(text=plugin.bot.get_me().username)

    if not access:
        await ctx.respond(embed=embed)
        return

    access_end_naive = access_end.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    remaining_time = access_end_naive - datetime.datetime.utcnow()

    till = f"<t:{int(access_end.timestamp())}:D>"
    ends = f"<t:{int(access_end.timestamp())}:R>"

    if remaining_time.days >= 999:
        till = "`None`"
        ends = "`Never`"

    embed = hikari.Embed(
        title="Access Info",
        color=utils.get_config()["color"],
        timestamp=datetime.datetime.now().astimezone()
    ).add_field("Till", till, inline=True)\
     .add_field("Ends", ends, inline=True)\
     .add_field("Active", f"`{access}`", inline=True)\
     .set_footer(text=plugin.bot.get_me().username)

    await ctx.respond(embed=embed)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.option("member", "Discord User", required=True, type=hikari.Member)
@lightbulb.command(name="get_user_access", description="Get User Access")
@lightbulb.implements(lightbulb.SlashCommand)
async def get_user_access(ctx: lightbulb.Context):
    member = getattr(ctx.options, "member", None)

    db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=member.id)
    data = await db.get_guild_member()

    access = data.get("has_access", False)
    access_end = data.get("access_end")

    if access_end:
        try:
            access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            try:
                access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:

                access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S")

    embed = hikari.Embed(
        title=f"Subscription Info",
        description=f"user: {member.mention}",
        color=utils.get_config()["color"],
        timestamp=datetime.datetime.now().astimezone()
    ).add_field("Till", "`None`", inline=True) \
        .add_field("Ends", "`None`", inline=True) \
        .add_field("Active", "`False`", inline=True) \
        .set_footer(text=plugin.bot.get_me().username)

    if not access:
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return


    else:

        till = f"<t:{int(access_end.timestamp())}:D>"
        ends = f"<t:{int(access_end.timestamp())}:R>"

        access_end_naive = access_end.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        remaining_time = access_end_naive - datetime.datetime.utcnow()

        if remaining_time.days >= 999:
            till = "`None`"
            ends = "`Never`"

        embed = hikari.Embed(
            title=f"Subscription Info",
            description=f"user: {member.mention}",
            color=utils.get_config()["color"],
            timestamp=datetime.datetime.now().astimezone()
        ).add_field("Till", till, inline=True) \
            .add_field("Ends", ends, inline=True) \
            .add_field("Active", f"`{access}`", inline=True) \
            .set_footer(text=plugin.bot.get_me().username)

    await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)

def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)