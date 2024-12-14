import functools
import json
import hikari
import miru


def check_author(func):
    @functools.wraps(func)
    async def wrapper(self, ctx: miru.ViewContext, *args, **kwargs):

        if ctx.author != self.command_user:
            return

        return await func(self, ctx, *args, **kwargs)

    return wrapper


def generate_doc_embed(documentations: list):
    embed = hikari.Embed(
        title="Error",
        color="#ff244c"
    )

    for doc in documentations:
        embed.add_field(doc.get("title"), doc.get("usage"))

    return embed

class GenerationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.config = get_config()
        self.error = message


    def generate_doc_embed(self) -> hikari.Embed:
        embed = hikari.Embed(
            title="Error",
            color="#ff244c"
        )

        error_documentation = self.config["error_docs"].get(self.error)
        if error_documentation is None:
            embed.add_field("Unspecified Error", "Please double check all your inputs")

        return embed.add_field(error_documentation.get("title"), error_documentation.get("usage"))



def format_price(price):
    if price.is_integer():
        price = int(price)
    else:
        price = "{:.2f}".format(round(price, 2))
    return price

def get_config():
    with open("receiptgen/config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
        file.close()

    return config
