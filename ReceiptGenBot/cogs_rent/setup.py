import aiohttp
import lightbulb
import hikari
from receiptgen import database

plugin = lightbulb.Plugin("public_setup")

@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="install_help", description="How to setup this bot")
@lightbulb.implements(lightbulb.SlashCommand)
async def setup_help(ctx: lightbulb.Context):

    embed = hikari.Embed(
        title="**Installation Help**",
        description="Before you can start using this bot it needs to be activated as\n"
                    "this is a paid service, **contact me here:**\n"
                    "- Discord server https://amethyx.net/invite\n"
                    "- Email 𝗰𝗼𝗻𝘁𝗮𝗰𝘁@𝗮𝗺𝗲𝘁𝗵𝘆𝘅.𝗻𝗲𝘁\n"
                    "\nBy using this bot you accept our TOS linked in our discord server"
    ).add_field(
        "/setup_channel - Admin Command",
        "This command is used to setup channel for subscription ended/added notifications and "
        "to setup a channel for purchasing which will be mentioned if a member does not have access to the generator"
    ).add_field(
        "/setup_role - Admin Command",
        "Selected role will be added to users when access is added to them, choose a role that is not above the bot"
        "so it can be managed by the bot"
    ).add_field(
        "/add_access - Admin Command",
        "This command is for adding access to users, you can specify the amount of days or choose forever"
    ).add_field(
        "/remove_access - Admin Command",
        "Used for removing access from users"
    ).add_field(
        "/get_user_access - Admin Command",
        "Will retrieve the selected users access information"
    ).add_field(
        "/manager - Admin Command",
        "Creates an admin user for server manager website "
        "you can login here: https://api.amethyx.net/admin"
    ).add_field(
        "/access - User Command",
        "Shows the users access information"
    ).add_field(
        "/menu and /generate - User Command",
        "Menu command for menu stuff and generate is basically a shortcut"
    )

    await ctx.respond(embed)

@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.command(name="manager", description="If ran the first time crates an admin user")
@lightbulb.implements(lightbulb.SlashCommand)
async def manager(ctx: lightbulb.Context):

    url = "http://localhost:8000/api/guild/add-owner/"

    data = {
        "guild_id": ctx.guild_id,
        "group_name": "Renter",
        "username": ctx.author.username
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            response = await response.json()

    if not response.get("error", False):
        await ctx.respond(
            "Manager was created and assigned to this server\n\n"
            "**Your Login Credentials**\n"
            f"username: `{response['username']}`\n"
            f"password: `{response['password']}`\n"
            f"Login in to https://api.amethyx.net/admin\n"
            f"and change your **temporary password** in the top right corner",
            flags=hikari.MessageFlag.EPHEMERAL
        )

    elif response.get("exists", False):
        await ctx.respond(
            "Manager was already assigned to this server\n"
            "you can login at https://api.amethyx.net/admin",
            flags=hikari.MessageFlag.EPHEMERAL
        )

    else:
        await ctx.respond(response["error"], flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.option(name="role", description="Choose a role", required=True, type=hikari.Role)
@lightbulb.command(name="setup_role", description="Setup access role that will be used by the bot")
@lightbulb.implements(lightbulb.SlashCommand)
async def setup_role(ctx: lightbulb.Context):
    role: hikari.Role = getattr(ctx.options, "role", None)
    guild_db = database.GuildAPI(guild_id=ctx.guild_id)
    result = await guild_db.updater_guild(access_role=role.id)

    if not result.get("error", False):
        await ctx.respond(f"{role.mention} will be used to track access", flags=hikari.MessageFlag.EPHEMERAL)

    else:
        await ctx.respond(result["error"], flags=hikari.MessageFlag.EPHEMERAL)

@plugin.command
@lightbulb.decorators.app_command_permissions(hikari.Permissions.ADMINISTRATOR, dm_enabled=False)
@lightbulb.option(name="channel", description="Choose a channel", required=True, type=hikari.TextableGuildChannel)
@lightbulb.option(name="option", description="Choose an option", choices=["notifications", "purchase"], required=True,)
@lightbulb.command(name="setup_channel", description="Setup commands to choose channels for bot")
@lightbulb.implements(lightbulb.SlashCommand)
async def setup_channel(ctx: lightbulb.Context):
    channel: hikari.TextableChannel = getattr(ctx.options, "channel", None)
    option = getattr(ctx.options, "option", None)


    guild_db = database.GuildAPI(guild_id=ctx.guild_id)

    if channel.type != hikari.ChannelType.GUILD_TEXT:
        await ctx.respond("Selected option is not a text channel", flags=hikari.MessageFlag.EPHEMERAL)
        return

    if option == "purchase":
        result = await guild_db.updater_guild(purchase_channel=channel.id)

    else:
        result = await guild_db.updater_guild(notification_channel=channel.id)

    if not result.get("error", False):
        await ctx.respond(f"{channel.mention} was selected as the {option} channel", flags=hikari.MessageFlag.EPHEMERAL)

    else:
        await ctx.respond(result["error"], flags=hikari.MessageFlag.EPHEMERAL)


def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)