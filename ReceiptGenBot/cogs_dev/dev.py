import asyncio
import lightbulb
import hikari
import miru
from receiptgen import ticketsystem, utils

plugin = lightbulb.Plugin("dev")
config = utils.get_config()


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="create_purchase_view", description="Creates a Persistent purchase view")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_purchase_embed(ctx: lightbulb.Context):
    view = ticketsystem.MainTicketView(timeout=None)

    await ctx.bot.rest.create_message(channel=ctx.channel_id, components=view, embed=view.embed)
    ctx.app.d.miru.start_view(view)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)

@plugin.listener(hikari.MessageCreateEvent)
async def image_link(event: hikari.MessageCreateEvent):
    if event.channel_id == config["images_channel"] and not event.is_bot:

        if len(event.message.attachments) != 1:
            response = await event.message.respond(
                content="Submit a single image only!",
                reply=True,
                mentions_reply=True
            )
            await asyncio.sleep(2)
            await response.delete()
            await event.message.delete()
            return

        image_url = event.message.attachments[0].url
        await event.message.respond(
            content="Here is your direct image link\n"
            f"```{image_url}```",
            reply=True,
            mentions_reply=True
        )

@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_honeypot", description="Creates a Honeypot Message")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_honeypot(ctx: lightbulb.Context):
    emoji = hikari.CustomEmoji(id=config["emojis"]["honeypot"], name="honeypot", is_animated=False)
    embed = hikari.Embed(
        title=f"Honey Pot {emoji}",
        description="**MESSAGING HERE WILL RESULT IN AN AUTOMATIC BAN**",
        color=config["color"]
    )
    await ctx.bot.rest.create_message(channel=ctx.channel_id, embed=embed)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_backup", description="Creates a Backup Message")
@lightbulb.implements(lightbulb.SlashCommand)
async def backup_server_msg(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title=f"Backup Server",
        description="Link your discord account so in the future you get joined in the backup server",
        color=config["color"]
    )

    view = miru.View().add_item(miru.LinkButton(url="oauth url", label="Link Account"))
    await ctx.bot.rest.create_message(
        channel=ctx.channel_id,
        embed=embed,
        components=view)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_examples", description="Creates Example Receipts in an Embed")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_examples(ctx: lightbulb.Context):
    await ctx.respond("creating embeds...", flags=hikari.MessageFlag.EPHEMERAL)

    for filename, title in config.get("example_receipts").items():
        embed = hikari.Embed(
            title=f"{title}",
            color=config["color"],
        ).set_image(f"images/receipts_preview/{filename}")
        await ctx.bot.rest.create_message(channel=ctx.channel_id, embed=embed)
        await asyncio.sleep(0.5)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_rules", description="Creates Rules in an Embed")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_rules(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title="Rules",
        description="**These rules appy to you even if you don't care to read them, so do read them**\n"
                    "- No spamming, posting weird shit or acting weird, just be normal\n"
                    "- Don't beg for access and don't ask other people to generate something for you\n"
                    "- Selling our receipts is strictly prohibited.\n"
                    "- Advertising is prohibited if you want to advertise contact us\n"
                    "- English only we can't moderate other languages so keep it in DM's\n"
                    "- You can ping but at least be nice about it and politely wait for an answer\n"
                    "- Most of all use common sense"
    )
    await ctx.bot.rest.create_message(channel=ctx.channel_id, embed=embed)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_info", description="Creates Rules in an Embed")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_info(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title="Info",
        description="Basic information about AmethyX",
        colour=config["color"]
    ).add_field(
        "Whats AmethyX?",
        "We provide a receipt generating service check out https://amethyx.net"
        "\ncurrently we are working to push out more and more brands"
    ).add_field(
        "How To Purchase?",
        "If you wish to purchase make a purchase ticket in <#1295862117487874098> more info in the channel"
    ).add_field(
        "Partnership?",
        "Sure if you provide something that could mutually benefit DM at <@846987673399066624>"
    ).add_field(
        "Vouch?",
        f"If you want to vouch for us, please do so in <#{config['vouch_channel']}>"
    ).add_field(
        "Free Access?",
        "If you have any email receipts that we don't have a generator for\n"
        "and are able to resend them to us via email"
        "you'll get free **Forever Access**\n"
        "Or get at least 15 invites from your invite link and for each 10 invites you'll get 1 Day of access, "
        "making tiktok videos is recommended"

    ).set_thumbnail("images/questionmark.png")
    await ctx.bot.rest.create_message(channel=ctx.channel_id, embed=embed)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="make_tos", description="Creates TOS in an Embed")
@lightbulb.implements(lightbulb.SlashCommand)
async def make_tos(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title="Terms of Service",
        description="By using our service, you acknowledge that you have read, understood, and agree to these Terms "
                    "of Service. "
    ).add_field(
        name="1. Acceptance of Terms",
        value="By using our service, you agree to comply with and be bound by these Terms of Service. If you do not "
              "agree with any part of these terms, please do not use our service. "
    ).add_field(
        name="2. No Liability",
        value="We are not liable for any damages, losses, or issues that may occur as a result of using our service. "
              "This includes, but is not limited to, any direct, indirect, incidental, or consequential damages. "
    ).add_field(
        name="3. Refund Policy",
        value="**Eligibility for Refunds**:\nTo request a refund, you must provide clear and verifiable proof that "
              "our service is not functioning as intended.\n\n**Conditions for Refunds**:\n- Refunds will only be "
              "processed if the service has not been fully utilized.\n- Refund requests must be submitted within one "
              "day from the date of purchase.\n\n**Proof Required**:\n- You must demonstrate that the service has "
              "failed to meet its promised functionality. "
    ).add_field(
        name="4. Modifications",
        value="We reserve the right to modify these Terms of Service at any time. Continued use of our service "
              "following any changes constitutes acceptance of the new terms. "
    ).add_field(
        name="5. Termination of Access",
        value="We reserve the right to terminate your access to this service at any time and for any reason. This "
              "includes, but is not limited to, breaches of these Terms of Service or violations of any server rules "
    ).add_field(
        name="6. Contact Information",
        value="For any questions or to request a refund, please DM Merks with the necessary details."
    ).set_footer("TOS updated on 9.8 2024")

    await ctx.bot.rest.create_message(channel=ctx.channel_id, embed=embed)
    await ctx.respond("Created successfully", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.command(name="promote", description="a bit of promotion comotion")
@lightbulb.implements(lightbulb.PrefixCommand)
async def promote(ctx: lightbulb.Context):
    if ctx.author.id != 1250179185058648157: return

    guilds = await ctx.bot.rest.fetch_my_guilds()
    blacklisted = [1267128976631926785, 1277301275901300780, 1259292241915150387, 1269322998909898852]

    await ctx.bot.rest.create_message(channel=ctx.channel_id, content=f"found {len(guilds)} guilds")
    for guild in guilds:

        await asyncio.sleep(0.5)
        guild_members = len(ctx.bot.cache.get_members_view_for_guild(guild.id))
        await ctx.bot.rest.create_message(channel=ctx.channel_id, content=f"{guild_members} members")
        if guild.id in blacklisted: continue
        channels = await ctx.bot.rest.fetch_guild_channels(guild=guild.id)

        channel_count = 0
        for channel in channels:

            if channel_count > 2: break

            try:
                await ctx.bot.rest.create_message(channel=channel.id,
                                                  content="Get Cheap Receipt Generator or Fake StockX app here:"
                                                          "\n discord.gg/amethyx\n"
                                                          "sorry for advertising but hey the owner added this bot\n"
                                                          "if you do not wish we advertise react with a checkmark"
                                                  )
                await ctx.bot.rest.create_message(channel=ctx.channel_id, content=f"message sent to {guild.name}")
                channel_count += 1

            except Exception as e:
                await ctx.bot.rest.create_message(channel=ctx.channel_id, content=e)
                await asyncio.sleep(0.2)

    # channels = await ctx.bot.rest.fetch_guild_channels(guild=ctx.guild_id)
    # for channel in channels:
    #     await ctx.bot.rest.create_message(channel=channel.id, content="")


def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)
