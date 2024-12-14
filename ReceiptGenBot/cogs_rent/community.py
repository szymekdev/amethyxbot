import asyncio

import lightbulb
import hikari
import miru

from receiptgen import utils, database

plugin = lightbulb.Plugin("public_community")
config = utils.get_config()


@plugin.command
@lightbulb.decorators.app_command_permissions(dm_enabled=False)
@lightbulb.command(name="updates", description="Get the latest updates")
@lightbulb.implements(lightbulb.SlashCommand)
async def get_updates(ctx: lightbulb.Context):
    updates_channel_id = config["updates_channel"]
    updates_channel = ctx.bot.rest.fetch_messages(channel=updates_channel_id)

    last_updates = await updates_channel.limit(5)
    updates = "**Last 5 Updates**\n\n"

    for message in reversed(last_updates):
        timestamp = message.timestamp.strftime("%I:%M %m/%d/%Y")
        updates += f"**[{timestamp}]**\n" \
                   f"{message.content}\n\n"

    await ctx.respond(content=updates, flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.command(name="guilds", description="Get all guilds")
@lightbulb.implements(lightbulb.PrefixCommand)
async def manage_guilds(ctx: lightbulb.Context):
    if ctx.author.id not in [846987673399066624, 1250179185058648157]: return

    await ctx.respond("fetching guilds:")
    guilds = await ctx.bot.rest.fetch_my_guilds()
    for guild in guilds:

        db = database.GuildAPI(guild.id)
        guild_info = await db.get_guild()
        status = guild_info.get('disabled')

        guild_members = await ctx.bot.rest.fetch_members(guild)

        if status is None and len(guild_members) < 50:
            await ctx.bot.rest.leave_guild(guild.id)
            await ctx.bot.rest.create_message(
                content=f"- ❌ left {guild.name}, members: {len(guild_members)}\n"
                        f" id: ```{guild.id}```",
                channel=ctx.channel_id
            )

        else:
            await ctx.bot.rest.create_message(
                content=f"- ✅ stayed {guild.name}, status {status}, members: {len(guild_members)}\n"
                        f" id: ```{guild.id}```",
                channel=ctx.channel_id
            )


class AdView(miru.View):

    def __init__(self, og_channel_id):
        super(AdView, self).__init__()
        self.og_channel_id = og_channel_id

    @miru.button(emoji="❌", style=hikari.ButtonStyle.SECONDARY, custom_id="jdoias")
    async def stop_ad(self, ctx: miru.ViewContext, button: miru.Button):

        if ctx.author == ctx.interaction.get_guild().owner_id:
            await plugin.bot.rest.create_message(
                channel=self.og_channel_id,
                content=f"{ctx.get_guild().name}, {ctx.guild_id}"
            )
            await ctx.respond("ads will be stopped", flags=hikari.MessageFlag.EPHEMERAL)

        else:
            await ctx.respond("you are not the owner", flags=hikari.MessageFlag.EPHEMERAL)

class ChannelButton(miru.View):

    def __init__(self, channel_id):
        super(ChannelButton, self).__init__()
        self.channel_id = channel_id

    @miru.button(label="send message")
    async def send_btn(self, ctx: miru.ViewContext, button: miru.Button):
        join_view = AdView(ctx.channel_id).add_item(
            miru.LinkButton(url="https://discord.gg/amethyx1", label="Join Now")
        )

        embed = hikari.Embed(
            title="🧾Get Email, Paper Receipts & Emulators🧾",
            description="AmethyX.net\n"
                        "we have over 270 customers and 1.5K members,"
                        " and I'd say were pretty cheap on the market\n"
                        "**Feel free to check out https://amethyx.net**  for videos and more info!",
            colour="#9966cc"
        ).set_image(
            "images/amethyx_public_banner.png"
        ).add_field(
            "Where to get?",
            "Click the button below labeled 'Join Now'\n"
            "You can even have this bot in your own server!"
        ).add_field(
            "Advertising?",
            "Owner of this server choose to add this bot, to stop this advertising press ❌"
        )
        try:
            await plugin.bot.rest.create_message(
                channel=self.channel_id,
                components=join_view.build(),
                embed=embed
            )
            plugin.app.d.miru.start_view(join_view)
            await ctx.respond("sent a message")

        except Exception as e:
            await ctx.respond(e)

@plugin.command
@lightbulb.option("channel_count", "channel id")
@lightbulb.option("guild", "guild id")
@lightbulb.command(name="advertise", description="gets all channels")
@lightbulb.implements(lightbulb.PrefixCommand)
async def get_channels(ctx: lightbulb.Context):
    if ctx.author.id not in [846987673399066624, 1250179185058648157]: return
    guild_id = getattr(ctx.options, "guild", None)
    channel_count = getattr(ctx.options, "channel_count", None)

    try: int(channel_count)
    except Exception as e:
        await ctx.respond(content=str(e))
        return

    await ctx.respond("fetching channels for guild id:")
    try:
        channels = await ctx.bot.rest.fetch_guild_channels(guild_id)

    except Exception as error:
        await ctx.respond(error)
        return

    for channel in channels[:int(channel_count)]:
        view = ChannelButton(channel.id)
        await ctx.bot.rest.create_message(
            channel=ctx.channel_id,
            content=channel.name,
            components=view.build()
        )
        ctx.app.d.miru.start_view(view)
        await asyncio.sleep(0.5)


@plugin.command
@lightbulb.option("guild", "guild id")
@lightbulb.command(name="kick", description="Kicks Bot from guild")
@lightbulb.implements(lightbulb.PrefixCommand)
async def kick_bot(ctx: lightbulb.Context):
    if ctx.author.id != 1250179185058648157: return
    guild_id = getattr(ctx.options, "guild", None)
    try:
        await ctx.bot.rest.leave_guild(guild_id)

    except (hikari.BadRequestError, hikari.NotFoundError) as error:
        await ctx.respond(error)


@plugin.command
@lightbulb.command(name="owner", description="shows if you are the owner")
@lightbulb.implements(lightbulb.PrefixCommand)
async def owner(ctx: lightbulb.Context):
    if ctx.author.id != 1250179185058648157: return
    await ctx.respond("You are the bot Owner", reply=True)


@plugin.command
@lightbulb.command(name="force-access", description="adds access role")
@lightbulb.implements(lightbulb.PrefixCommand)
async def force_access(ctx: lightbulb.Context):
    if ctx.author.id != 1250179185058648157: return
    try:
        await ctx.event.message.delete()
    except hikari.ForbiddenError:
        pass

    db = database.GuildAPI(ctx.guild_id)
    guild_data = await db.get_guild()

    db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=ctx.author.id)
    await db.update_guild_member(days=99999)

    if guild_data.get("access_role"):
        await ctx.bot.rest.add_role_to_member(
            guild=ctx.guild_id,
            role=int(guild_data.get("access_role")),
            user=ctx.author.id
        )


def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)
