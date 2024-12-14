import datetime
import hikari
import lightbulb
import miru
from miru.ext import menu
from receiptgen import receiptgen, utils, database

plugin = lightbulb.Plugin("menu")
config = utils.get_config()



async def send_email_and_update_menu(ctx, brand, product, rmenu: menu.Menu):
    embed = hikari.Embed(
        title="Sending Email",
        description="*sending receipt to your email*",
    ).set_image("images/progress_4.gif")
    await ctx.edit_response(embed=embed, attachments=[], components=[])

    member_db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=ctx.author.id)
    member_data = await member_db.get_guild_member()
    email = member_data["email"]

    try:
        await brand.generate_email(
            product,
            email
        )

    except utils.GenerationError as e:

        # respond with error doc embed
        await ctx.respond(embed=e.generate_doc_embed(), flags=hikari.MessageFlag.EPHEMERAL)
        await rmenu.pop(count=1)
        return

    except Exception as e:
        embed = hikari.Embed(
            title="Unknown Error",
            description="An unknown issue occurred",
        ).set_image("images/progress_0.gif")
        await rmenu.message.edit(embed=embed, attachments=[], components=[])
        rmenu.stop()
        raise e

    embed = hikari.Embed(
        title="Receipt Sent Successfully",
        description="*Generated receipt was sent to your email, if it lands in spam mark it as not spam*",
        color=config["color"],
        timestamp=datetime.datetime.now().astimezone()
    ).set_image("images/progress_5.gif") \
        .set_footer(text="House of Hustlers")

    await rmenu.message.edit(embed=embed)
    rmenu.stop()


class ReceiptOptionBtn(menu.ScreenButton):
    def __init__(self, product, brand, label):
        super(ReceiptOptionBtn, self).__init__(style=hikari.ButtonStyle.SECONDARY, label=label)
        self.product = product
        self.brand = brand

    async def callback(self, ctx: miru.ViewContext) -> None:
        for name, value in self.product.get("options")[self.label].items():
            self.product[name] = value
        del self.product["options"]

        await send_email_and_update_menu(
            ctx,
            self.brand,
            self.product,
            self.menu
        )


class ReceiptOptions(menu.Screen):

    def __init__(self, menu_: menu.Menu):
        super().__init__(menu_)

    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Options",
                description="*select an option for the given product*",
                color=config["color"],
            ).set_image("images/progress_3.gif")
        )


class ReceiptStepTwo(menu.Screen):

    def __init__(self, menu_: menu.Menu, brand):
        super().__init__(menu_)
        self.brand = brand
        self.prev_input = None

    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Step Two",
                description="*Complete the next Step*",
                color=config["color"],
            ).set_image("images/progress_2.gif")
        )

    @menu.button(label="Next")
    async def step_two(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:


        if self.menu.prev_input:
            self.brand.user_input = self.menu.prev_input

        modal = await self.brand.get_step_two()
        await ctx.respond_with_modal(modal)
        await modal.wait()

        if modal.brand.user_input.error:

            # store prev inputs
            self.menu.prev_input = modal.brand.user_input

            # make error doc embed
            error_documentations = modal.brand.user_input.error_documentations
            embed = utils.generate_doc_embed(error_documentations)

            # update screen and button
            button.label = "try again"
            await self.menu.update_message()
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        embed = hikari.Embed(
            title="Generating Receipt",
            description="*please wait till the receipt is generated*",
            color=config["color"],
        ).set_image("images/progress_3.gif")

        await ctx.edit_response(embed=embed, attachment=[], components=[])

        try:
            product = await modal.brand.scrape_web()
            options = product.get("options", False)


        except utils.GenerationError as e:
            await ctx.respond(embed=e.generate_doc_embed(), flags=hikari.MessageFlag.EPHEMERAL)
            await self.menu.update_message(await self.build_content())
            return

        except Exception as e:
            embed = hikari.Embed(
                title="Unknown Error",
                description="An unknown issue occurred",
            ).set_image("images/progress_0.gif")

            # stop and remove components
            await self.menu.message.edit(embed=embed, attachments=[], components=[])
            self.menu.stop()
            raise e

        if options:

            options_screen = ReceiptOptions(self.menu)

            for option in options:
                options_screen.add_item(
                    ReceiptOptionBtn(
                        product,
                        self.brand,
                        option
                    )
                )

            await self.menu.push(options_screen)
            return

        await send_email_and_update_menu(
            ctx,
            self.brand,
            product,
            self.menu
        )


class BackButton(menu.ScreenButton):
    def __init__(self):
        super().__init__(emoji="⬅️", position=1)

    async def callback(self, ctx: miru.ViewContext) -> None:
        await self.menu.pop()

async def service_disabled_embed():
    embed = hikari.Embed(
        title="Service Disabled",
        description="It looks like your bot subscription has not been paid."
                    "Please renew your subscription to continue using the service.\n"
                    "**if you think that this was a mistake please contact me here contact@amethyx.net**"
    )
    return embed

class ReceiptStepOne(menu.Screen):

    def __init__(self, menu_: menu.Menu, **kwargs) -> None:
        super().__init__(menu_)
        self.spoof = False
        self.disabled_notif_sent = False

    async def build_content(self) -> menu.ScreenContent:

        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Brand Selector",
                description="*Please select a brand that you would like to generate a receipt for*",
                color=config["color"],
            ).set_image("images/progress_1.gif")
        )

    # gather options
    options = []
    for name, info in receiptgen.brand_options.items():
        options.append(miru.SelectOption(label=name, emoji=info[1], value=name))

    @menu.text_select(
        placeholder="Select a brand", options=options
    )
    async def slm_brand(self, ctx: miru.ViewContext, select: miru.TextSelect) -> None:

        guild_db = database.GuildAPI(guild_id=ctx.guild_id)
        guild_data = await guild_db.get_guild()

        if guild_data.get("disabled", True) and not self.disabled_notif_sent:
            self.disabled_notif_sent = True
            await ctx.respond(embed=await service_disabled_embed())
            return

        elif self.disabled_notif_sent:
            await ctx.edit_response()
            return


        member_db = database.GuildMemberAPI(
            guild_id=ctx.guild_id,
            member_id=ctx.author.id
        )
        member_data = await member_db.get_guild_member()
        member_roles = ctx.member.get_roles()
        has_access = False

        for role in member_roles:
            if role.id == int(guild_data.get("access_role")):
                has_access = True

        if not has_access:
            channel_id = guild_data.get("purchase_channel", None)
            channel = await ctx.client.bot.rest.fetch_channel(channel=channel_id)
            embed = hikari.Embed(
                title="No Access",
                description=f"You dont have access to {plugin.app.application.name} receipt Generator"
                            f"\n more info about purchasing in {channel.mention}"
            )

            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if member_data.get("email", None) is None:
            await ctx.respond("Please set up your email using /menu", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # get brand from brand options list
        brand = receiptgen.brand_options.get(select.values[0])[0]


        if self.menu.prev_input:
            brand = brand()
            brand.user_input = self.menu.prev_input

        else:
            brand = brand()

        # get the first modal
        modal = await brand.get_step_one()

        # show the first modal
        await ctx.respond_with_modal(modal)
        await modal.wait()

        self.menu.prev_input = brand.user_input

        if modal.brand.user_input.error:

            error_documentations = modal.brand.user_input.error_documentations
            embed = utils.generate_doc_embed(error_documentations)
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        else:
            brand.set_spoof(self.spoof)
            await self.menu.push(
                ReceiptStepTwo(self.menu, brand).add_item(BackButton())
            )

    @menu.button(emoji="🔄")
    async def restart(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:
        self.menu.prev_input = None
        await self.menu.update_message()

    @menu.button(emoji="✖", style=hikari.ButtonStyle.DANGER)
    async def close(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:
        embed = self.menu.message.embeds[0]

        embed = hikari.Embed(
            title=f"{embed.title} [Closed]",
            description=embed.description,
        ).set_image("images/progress_0.gif")

        await self.menu.message.edit(embed=embed, attachment=[], components=[])
        self.menu.stop()



class EmailSetup(miru.Modal):
    email = miru.TextInput(label="Your Email")
    email_confirm = miru.TextInput(label="Confirm Your Email")

    async def callback(self, ctx: miru.ModalContext, ) -> None:

        if self.email.value != self.email_confirm.value:
            await ctx.respond(
                "Emails don't match, please try again",
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        member_db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=ctx.author.id)
        result = await member_db.update_guild_member(email=self.email.value)

        if not result.get("error"):
            await ctx.respond(
                "Your email has been successfully set up",
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        await ctx.respond(
            "Something went wrong",
            flags=hikari.MessageFlag.EPHEMERAL
        )


class MainMenu(menu.Screen):

    def __init__(self, menu_: menu.Menu, guild_data):
        super(MainMenu, self).__init__(menu_)
        self.guild_data = guild_data
        self.disabled_notif_sent = False

    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Main Menu",
                color="#9966cc",
                timestamp=datetime.datetime.now().astimezone()
            ).set_footer(text="House of Hustlers")
                .add_field("Generate", "This will take you to the generator")
                .add_field("Purchase", "If you haven't purchased yet here is the list of "
                                       "all the available brands\n and how to purchase")
                .add_field("Setup Email", "IMPORTANT before generating anything please set up your email")
        )

    @menu.button(label="Generate", style=hikari.ButtonStyle.SUCCESS)
    async def generate(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:
        screen = ReceiptStepOne(self.menu, ).add_item(BackButton())
        await self.menu.push(screen)

    @menu.button(label="Purchase", style=hikari.ButtonStyle.SECONDARY)
    async def purchase(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:
        if self.guild_data.get("disabled", True) and not self.disabled_notif_sent:
            self.disabled_notif_sent = True
            await ctx.respond(embed=await service_disabled_embed())
            return

        elif self.disabled_notif_sent:
            await ctx.edit_response()
            return

        await ctx.respond(f"More info about purchasing here <#{self.guild_data.get('purchase_channel')}>",
                          flags=hikari.MessageFlag.EPHEMERAL)

    @menu.button(label="SetupEmail", style=hikari.ButtonStyle.SECONDARY)
    async def setup_email(self, ctx: miru.ViewContext, button: menu.ScreenButton) -> None:
        member_db = database.GuildMemberAPI(guild_id=ctx.guild_id, member_id=ctx.author.id)
        member_data = await member_db.get_guild_member()

        if self.guild_data.get("disabled", True) and not self.disabled_notif_sent:
            self.disabled_notif_sent = True
            await ctx.respond(embed=await service_disabled_embed())
            return

        elif self.disabled_notif_sent:
            await ctx.edit_response()
            return

        if member_data.get("email"):
            await ctx.respond("You have already set up your email, if you wish to change it please request an email "
                              "change from us. "
                              "We allow email changes under strict conditions only",
                              flags=hikari.MessageFlag.EPHEMERAL)
            return

        modal = EmailSetup("Setup Email")
        await ctx.respond_with_modal(modal)
        await modal.wait()


class BaseMenu(menu.Menu):

    def __init__(self, user: hikari.User, *args, **kwargs):
        self.user: hikari.User = user
        self.prev_input = None
        super().__init__(timeout=360)

    async def view_check(self, ctx: miru.ViewContext) -> bool:
        return ctx.user.id == self.user.id

    async def on_timeout(self) -> None:

        if not self.message:
            return

        embed = self.message.embeds[0]

        if embed.title == "Receipt Sent Successfully":
            return

        embed = hikari.Embed(
            title=f"{embed.title} [Closed]",
            description=embed.description,
        ).set_image("images/progress_0.gif")

        try:
            await self.message.edit(components=[], attachments=[], embed=embed)

        except AttributeError: pass



@plugin.command
@lightbulb.decorators.app_command_permissions(dm_enabled=False)
@lightbulb.decorators.add_cooldown(30, 1,  lightbulb.UserBucket)
@lightbulb.command(name="generate", description="Receipt Generator")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def generate(ctx: lightbulb.Context):
    my_menu = BaseMenu(ctx.user)
    client = ctx.app.d.miru
    builder = await my_menu.build_response_async(
        client,
        ReceiptStepOne(my_menu, guild_id=ctx.guild_id, command_user=ctx.author.id)
    )
    await builder.respond_with_tanjun(context=ctx)
    client.start_view(my_menu)

@plugin.command
@lightbulb.decorators.app_command_permissions(dm_enabled=False)
@lightbulb.decorators.add_cooldown(30, 1,  lightbulb.UserBucket)
@lightbulb.command(name="menu", description="Everything you need in one menu")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def main_menu(ctx: lightbulb.Context):

    my_menu = BaseMenu(ctx.user)
    client = ctx.app.d.miru

    guild_db = database.GuildAPI(guild_id=ctx.guild_id)
    guild_data = await guild_db.get_guild()

    builder = await my_menu.build_response_async(
        client,
        MainMenu(
            my_menu,
            guild_data
        )
    )
    await builder.respond_with_tanjun(context=ctx)
    client.start_view(my_menu)


def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)
