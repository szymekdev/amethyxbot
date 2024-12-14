import asyncio
import datetime
import os
import random
import stripe
from miru.ext import menu
import miru
import hikari
from receiptgen import utils, database, receiptgen

config = utils.get_config()
payment_options = {
    "Card": "💳",
    "PayPal": hikari.CustomEmoji(id=config['emojis']['paypal_icon'], name="paypal_icon", is_animated=False),
    "Other": hikari.CustomEmoji(id=config['emojis']['stripe_icon'], name="stripe_icon", is_animated=False),
    "GooglePay": hikari.CustomEmoji(id=config['emojis']['google_pay_icon'], name="google_pay_icon", is_animated=False),
    "ApplePay": hikari.CustomEmoji(id=config['emojis']['applepay_icon'], name="applepay_icon", is_animated=False),
    "MobilePay": hikari.CustomEmoji(id=config['emojis']['mobile_pay_icon'], name="mobile_pay_icon", is_animated=False),
    "Link": hikari.CustomEmoji(id=config['emojis']['link_icon'], name="link_icon", is_animated=False),
    "Blik": hikari.CustomEmoji(id=config['emojis']['blik_icon'], name="blik_icon", is_animated=False)
}

stripe.api_key = os.getenv("STRIPE_KEY")


class CloseConfirm(miru.View):
    def __init__(self):
        super().__init__(timeout=None)

    @miru.button(label="Confirm")
    async def confirm(self, ctx: miru.ViewContext, button: miru.Button):
        await ctx.edit_response()
        asyncio.create_task(ctx.get_channel().delete())


class TicketChannelView(miru.View):
    def __init__(self):
        super().__init__(timeout=None)

    @miru.button(label="Close Ticket", style=hikari.ButtonStyle.DANGER, custom_id=f"{random.randint(1000, 99999)}")
    async def close(self, ctx: miru.ViewContext, button: miru.Button):
        close_confirm = hikari.Embed(
            title="Do you wist to close your ticket?",
            timestamp=datetime.datetime.now().astimezone()
        )

        close_view = CloseConfirm()
        await ctx.respond(components=close_view, embed=close_confirm, flags=hikari.MessageFlag.EPHEMERAL)
        ctx.client.start_view(close_view)


class SetupTicket:

    def __init__(self, payment_option, subscription, bot, client, user_id, guild):
        self.payment_option = payment_option
        self.subscription = subscription
        self.bot = bot
        self.client = client
        self.user_id = user_id
        self.guild = guild

    async def setup_ticket_channel(self, channel):
        subscription = config["ticketsystem"]["subscriptions"][self.subscription]

        try:
            url = self.create_stripe_payment_link()

        except Exception as e:
            await channel.send(
                content="Something went wrong while creating your payment link",
                components=TicketChannelView()
            )
            raise e

        timestamp = datetime.timedelta(days=1) + datetime.datetime.now()
        timestamp = f"**<t:{int(timestamp.timestamp())}:R>**"
        embed = hikari.Embed(
            title="Payment",
            description="Click on Payment Link, this will take you to stripe "
                        "and after payment you'll be granted access automatically"
                        "\n\n**If you need any help or have any questions just message here**\n"
                        f"Ticket closes in: {timestamp}",
            color=config["color"],
            timestamp=datetime.datetime.now().astimezone()
        ).add_field("Amount", f"{subscription['price']}€")

        ticket_channel_view = TicketChannelView().add_item(
            miru.LinkButton(
                url=url,
                label="Payment Link"
            )
        )

        await channel.send(components=ticket_channel_view, embed=embed)
        self.client.start_view(ticket_channel_view)

    def create_stripe_payment_link(self):

        stripe_price = config["ticketsystem"]["subscriptions"][self.subscription]["stripe_price"]
        currency = "EUR"

        if self.payment_option == "Other":
            payment_method_types = None

        elif self.payment_option in ["ApplePay", "GooglePay"]:
            payment_method_types = ["card"]

        elif self.payment_option == "Link":
            payment_method_types = ["card", "link"]

        elif self.payment_option == "Blik":
            payment_method_types = [self.payment_option.lower()]
            currency = "PLN"

        else:
            payment_method_types = [self.payment_option.lower()]

        payment_link = stripe.PaymentLink.create(
            line_items=[
                {'price': stripe_price,
                 "quantity": 1
                 }
            ],
            metadata={
                'user_id': self.user_id,
                'subscription': self.subscription
            },
            custom_text={
                "after_submit": {
                    "message": "AmethyX will grant you access shortly"
                }
            },
            restrictions={
                "completed_sessions": {
                    "limit": 1
                }
            },
            inactive_message="Payment link is no longer active please create another ticket",
            after_completion={
                "type": "redirect",
                "redirect": {
                    "url": f"https://discord.com/channels/{self.guild}/{config['notification_channel']}"
                }
            },
            payment_method_types=payment_method_types,
            currency=currency,
            allow_promotion_codes=True
        )
        return payment_link["url"]

    async def create_ticket(self, member):
        user_overwrite = hikari.PermissionOverwrite(
            type=hikari.PermissionOverwriteType.MEMBER,
            id=member.id,
            allow=(hikari.Permissions.SEND_MESSAGES
                   | hikari.Permissions.ADD_REACTIONS
                   | hikari.Permissions.ATTACH_FILES
                   | hikari.Permissions.USE_EXTERNAL_EMOJIS
                   | hikari.Permissions.VIEW_CHANNEL
                   ),
        )

        everyone_overwrite = hikari.PermissionOverwrite(
            type=hikari.PermissionOverwriteType.ROLE,
            id=self.guild,
            deny=hikari.Permissions.VIEW_CHANNEL,
        )

        category = config["ticketsystem"]["category"]
        channel = await self.bot.rest.create_guild_text_channel(
            guild=self.guild,
            name=f"temp-{random.randint(100, 999)}",
            category=category,
            permission_overwrites=[user_overwrite, everyone_overwrite]
        )
        result = await database.Ticket.create_ticket(channel_id=channel.id, user_id=member.id)

        if result is None:
            await channel.delete()
            return result

        asyncio.create_task(channel.edit(name=f"ticket-{result}"))
        asyncio.create_task(self.setup_ticket_channel(channel))
        channel_url = f"https://discord.com/channels/{self.guild}/{channel.id}"

        return channel_url


class PaymentOptionBtn(menu.ScreenButton):
    def __init__(self, label, emoji, subscription) -> None:
        super().__init__(label=label, style=hikari.ButtonStyle.SECONDARY, emoji=emoji)
        self.subscription = subscription

    async def callback(self, ctx: miru.ViewContext):
        ticket = SetupTicket(
            bot=ctx.client.bot,
            client=ctx.client,
            payment_option=self.label,
            subscription=self.subscription,
            user_id=ctx.user.id,
            guild=ctx.guild_id
        )

        channel_url = await ticket.create_ticket(member=ctx.member)

        if channel_url:

            embed = hikari.Embed(
                title="Purchase Menu",
                color="#9966cc",
                description="A ticket has been created for you",
                timestamp=datetime.datetime.now().astimezone()
            )

            row = self.menu.client.app.rest.build_message_action_row().add_link_button(
                channel_url,
                label="Ticket"
            )
            self.menu.clear_items()
            await ctx.edit_response(embed=embed, components=[row])


        else:
            embed = hikari.Embed(
                title="Purchase Menu",
                color="#9966cc",
                description="You may have exceeded the ticket limit, try to close your old one",
                timestamp=datetime.datetime.now().astimezone()
            )
            await ctx.edit_response(embed=embed, flags=hikari.MessageFlag.EPHEMERAL, components=[])
            self.menu.stop()


class PaymentOptionScreen(menu.Screen):

    def __init__(self, menu_: menu.Menu):
        super(PaymentOptionScreen, self).__init__(menu_)

    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Purchase Menu",
                color="#9966cc",
                description="Select a payment method",
                timestamp=datetime.datetime.now().astimezone()
            )
        )


class SubscriptionOptionBtn(menu.ScreenButton):

    def __init__(self, label):
        super().__init__(label=label, style=hikari.ButtonStyle.SECONDARY)

    async def callback(self, ctx: miru.ViewContext):
        payment_options_screen = PaymentOptionScreen(self.menu)
        for payment_name, emoji in payment_options.items():
            payment_options_screen.add_item(
                PaymentOptionBtn(label=payment_name, emoji=emoji, subscription=self.label))

        await self.menu.push(payment_options_screen)


class BuyMenu(menu.Screen):

    def __init__(self, menu_: menu.Menu):
        super(BuyMenu, self).__init__(menu_)

    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
                title="Purchase Menu",
                color="#9966cc",
                description="Select which product you would like to purchase\n"
                            "first 3 are options for Email Receipts",
                timestamp=datetime.datetime.now().astimezone()
            )
        )


class MainTicketView(miru.View):
    payment_options_field = ""
    brands_field = ""
    arrow_emoji = hikari.CustomEmoji(id=config['emojis']['arrow_icon'], name="arrow_icon", is_animated=False)

    for emoji in payment_options.values():
        payment_options_field += f" {emoji}"

    for brand in receiptgen.brand_options.keys():
        brands_field += f"{brand} "

    embed = hikari.Embed(
        title="Create Purchase Ticket",
        description="This menu will take you to a private ticket\n where you can continue the payment process",
        color="#9966cc"
    ).add_field(
        f"{arrow_emoji} Email Receipt Generator",
        "- Day **5€**\n"
        "- Week **15€**\n"
        "- Forever **20€**\n"
        "‎[Video preview](https://www.youtube.com/watch?v=3BMXGH-HUJU&ab_channel=AmethyX)\n"
        f"{brands_field}\n‎ "
    ).add_field(
        f"{arrow_emoji} Emulators (fake app)",
        "- Forever Access **10€**\n"
        "‎[Video preview](https://www.youtube.com/watch?v=dxkzq0DkAlc)\n"
        "Currently we offer stockx.com emulator, with this you can simulate in-app purchases from StockX\n‎ "
    ).add_field(
        f"{arrow_emoji} Paper Receipt Maker",
        "- Forever Access **20€**\n"
        "‎[Video preview](https://www.youtube.com/watch?v=wKteOpMZ6HU&t=23s&ab_channel=AmethyX)\n"
        "Apple StockX Nike\n‎ "
    ).add_field(
        f"{arrow_emoji} Full Package **Save 20%**",
        "- Includes All Above **40€**\n‎ "
    ).add_field(
        "Payment Options", f"{payment_options_field}\n‎ "
    ).add_field(
        "How does it work?",
        "AmethyX will create a **stripe payment link** depending on selected payment "
        "method so your payment goes securely "
        "through stripe.com after payment **you'll be granted access automatically**"
    ).set_thumbnail("images/dollar.png")

    @miru.button(label="Purchase", custom_id="ffff", style=hikari.ButtonStyle.SUCCESS)
    async def proceed_btn(self, ctx: miru.ViewContext, button: miru.Button):
        # todo load config from api
        my_menu = menu.Menu()
        client = ctx.client
        buy_menu = BuyMenu(my_menu)

        for subscription, conf in config["ticketsystem"]["subscriptions"].items():
            buy_menu.add_item(SubscriptionOptionBtn(label=subscription))

        builder = await my_menu.build_response_async(client, buy_menu, ephemeral=True)
        await ctx.respond_with_builder(builder)
        client.start_view(my_menu)
