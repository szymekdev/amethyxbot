import asyncio
import json
import datetime
import os
import hikari
import lightbulb
import miru
from lightbulb.ext import tasks
from receiptgen import database, utils
from aiohttp import web

token = os.getenv("BOT_KEY")

bot = lightbulb.BotApp(token=token,
                       intents=hikari.Intents.GUILD_MEMBERS | hikari.Intents.MESSAGE_CONTENT | hikari.Intents.GUILDS | hikari.Intents.ALL_MESSAGES,
                       default_enabled_guilds=[1255986026669674616],
                       prefix="!"
                       )

bot.d.miru = miru.Client(bot, ignore_unknown_interactions=True)
routes = web.RouteTableDef()
tasks.load(bot)

@bot.listen(hikari.GuildJoinEvent)
async def on_join(event: hikari.GuildJoinEvent):
    channel = await event.guild.fetch_system_channel()

    if channel is None:
        channel = await event.guild.fetch_public_updates_channel()

    if channel is None:
        return

    embed = hikari.Embed(
        title="Setup Info",
        description="Before you can start using this bot it needs to be activated as\n"
                    "this is a paid service, **contact me here:**\n"
                    "- Discord server https://amethyx.net/invite\n"
                    "- Email 𝗰𝗼𝗻𝘁𝗮𝗰𝘁@𝗮𝗺𝗲𝘁𝗵𝘆𝘅.𝗻𝗲𝘁\n"
                    "\nBy using this bot you accept our TOS linked in our discord server",
        colour=config["color"]
    ).add_field(
        "Features",
        "Main feature of this bot is a user friendly interface"
        "and a member management website where you can log in and see all your members"
        "and their information\n"
        "**See all the features and how to setup /install_help**"
    ).set_image(
        "images/amethyx_public_banner.png"
    )

    await bot.rest.create_message(channel=channel, embed=embed)

@bot.listen(hikari.StartedEvent)
async def on_start(event: hikari.StartedEvent):
    await bot.update_presence(
        status=hikari.Status.ONLINE,
        activity=hikari.Activity(
            name="Check my Bio",
            type=hikari.ActivityType.WATCHING,
        ),
    )

    await runner.setup()
    webserver = web.TCPSite(runner, host='localhost', port=6000)
    await webserver.start()

@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent) -> None:

    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lightbulb.CommandIsOnCooldown):
        await event.context.respond(f"Command is on cooldown. Retry in `{exception.retry_after:.2f}` seconds.",
                                    flags=hikari.MessageFlag.EPHEMERAL)
        return

    else:
        raise exception


config = utils.get_config()

async def access_notif(state, user_id, guild_data):
    member = await bot.rest.fetch_member(guild=guild_data.get("guild_id"), user=user_id)
    notification_channel = guild_data.get("notification_channel")

    if not notification_channel:
        return

    if state == "added":

        embed = hikari.Embed(
            title="Access Added",
            description=f"Thank you for purchasing {member.mention}"
                        f"\nyou can now use the receipt generator by typing\n /menu or /generator",
            color=config["color"]
        )


    elif state == "removed":
        embed = hikari.Embed(
            title="Subscription Expired",
            description=f"{member.mention}, your subscription has ended, and access to the receipt generator has been "
                        f"removed",
            color="#ff244c",
            timestamp=datetime.datetime.now().astimezone()
        )

    else:
        return None

    await bot.rest.create_message(embed=embed, channel=notification_channel)


@routes.post("/add-access-role")
async def add_access_role(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.Response(text="Invalid JSON", status=400)

    guild_db = database.GuildAPI(guild_id=data["guild_id"])
    guild_data = await guild_db.get_guild()

    if guild_data.get("access_role"):
        asyncio.create_task(bot.rest.add_role_to_member(
            guild=int(data["guild_id"]),
            user=int(data["user_id"]),
            role=guild_data["access_role"],
            )
        )
    asyncio.create_task(access_notif("added", int(data["user_id"]), guild_data))

    return web.Response(text="success")

app = web.Application()
app.add_routes(routes)
runner = web.AppRunner(app)

@bot.listen()
async def cleanup_webserver(_: hikari.StoppingEvent):
    await runner.cleanup()

status_messages = ["Check my Bio", "Generating Receipts"]
sm_pos = 0
@tasks.task(s=20, auto_start=True)
async def change_status():
    global sm_pos
    await bot.update_presence(
        status=hikari.Status.ONLINE,
        activity=hikari.Activity(
            name=status_messages[sm_pos],
            type=hikari.ActivityType.WATCHING,
        ),
    )
    if sm_pos < len(status_messages)-1:
        sm_pos += 1
    else: sm_pos = 0

@tasks.task(m=1, auto_start=True)
async def remove_access_roles():
    guild_db = database.GuildAPI()

    for guild_member in await guild_db.members_without_access():

        member_guild = guild_member.get("guild")
        guild_db = database.GuildAPI(guild_id=member_guild)
        guild_data = await guild_db.get_guild()

        if guild_data.get("access_role"):
            try:
                await bot.rest.remove_role_from_member(
                    guild=guild_data["guild_id"],
                    role=guild_data["access_role"],
                    user=guild_member.get("member")
                )
            except hikari.ForbiddenError: print("couldn't remove role for member")

        asyncio.create_task(access_notif(state="removed", user_id=guild_member.get("member"), guild_data=guild_data))


bot.load_extensions_from("./cogs_rent/")
bot.load_extensions_from("./cogs_shared/")
bot.run()