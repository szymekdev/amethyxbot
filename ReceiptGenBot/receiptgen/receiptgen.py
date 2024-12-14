import asyncio
import json
import os
import string
from datetime import datetime, timedelta
from random import randint, choice, choices, sample
from urllib.parse import urlparse
import aiohttp
import hikari
import miru
from bs4 import BeautifulSoup
import aiosmtplib
from email.message import EmailMessage
from receiptgen import database, utils, input_validator
from typing import Optional

class ReceiptModal(miru.Modal):
    """ universal modal used in every brand class to build the form """

    def __init__(self, brand):
        super().__init__(title=brand.title)
        self.brand = brand

    async def callback(self, ctx: miru.ModalContext) -> None:
        await self.brand.user_input_validation([text_input for text_input, value in ctx.values.items()])
        await ctx.edit_response()


class Brand:
    def __init__(self):
        self.user_input = None
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
                          ' like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        self.spoof = False

        self.address_placeholder1 = "1. Street\n2. City\n3. Zip Code\n4. Country"
        self.address_placeholder2 = "1. Street\n2. City\n3. Country & Zip Code"
        self.address_placeholder3 = "1. Street\n2. City\n3. Country"
        self.title = "Default"

    async def user_input_validation(self, text_inputs: list) -> None:
        await self.user_input.validate(text_inputs)

    @staticmethod
    def get_scrape_data() -> dict:
        with open("receiptgen/scrape_data.json", "r") as scrape_data_file:
            scrape_data = json.load(scrape_data_file)

        return scrape_data

    @staticmethod
    def get_spoof_date(date):
        input_date = datetime.strptime(date, "%m/%d/%Y")
        current_datetime = datetime.now()
        combined_datetime = input_date.replace(hour=current_datetime.hour, minute=current_datetime.minute)
        output_date_str = combined_datetime.strftime("%d. %m. %Y %H:%M")

        return output_date_str

    @staticmethod
    def get_template(name, spoof) -> str:
        with open(f"receiptgen/templates/{name}.html", "r", encoding="utf-8") as template_file:
            template = template_file.read()

        return template

    def set_spoof(self, enabled=True):
        self.spoof = enabled


    @staticmethod
    async def send_email(to_email, html_content, subject, sender_name, spoofed_email=None):
        smtp_server = ""
        smtp_port = 587
        smtp_user = ""
        smtp_password = ""

        msg = EmailMessage()
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Sender"] = smtp_user
        msg["Reply-To"] = f"{sender_name} <{smtp_user}>"
        msg.set_content("plain text email, this shouldn't be visible")
        msg.add_alternative(html_content, subtype='html')

        smtp = None
        try:
            smtp = aiosmtplib.SMTP(hostname=smtp_server, port=smtp_port, use_tls=False)
            await smtp.connect()

            if not smtp:
                await smtp.starttls()

            await smtp.login(smtp_user, smtp_password)
            await smtp.send_message(msg)

        except Exception:
            if smtp:

                try:
                    await smtp.quit()
                except Exception:
                    pass

            raise utils.GenerationError("email")


        finally:
            if smtp:
                await smtp.quit()

    async def fetch_web(
            self,
            headers: Optional[dict] = None,
            url: Optional[str] = None,
            cookies: Optional[str] = None,
            params: Optional[dict] = None,
    ):
        if headers is None:
            headers = self.default_headers

        if url is None:
            url = self.user_input.validated["url"]

        scraped_db = database.ScrapedWebLink(url)
        data = await scraped_db.get_scraped_content()

        if data:
            return data

        try:

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url=url, headers=headers, cookies=cookies, params=params) as response:
                    if response.status != 200:
                        raise aiohttp.ClientConnectionError

                    data = await response.text(encoding="utf-8")

        except Exception as e:
            raise e

        asyncio.create_task(
            database.ScrapedWebLink(url).save_scraped_content(
                content=data,
                title=self.title,
            ))

        return data


class UserInput:
    error: bool
    validated: dict
    error_documentations: list

    def __init__(self):

        self.error_documentations = []
        self.validated = {}
        self.error = False
        self.values = {}

    async def validate(self, text_inputs):

        self.error_documentations = []
        self.error = False

        for text_input in text_inputs:

            self.values[text_input.custom_id] = text_input.value

            try:
                valid_data = await text_input.run_check()

                self.validated[text_input.custom_id] = valid_data

            except input_validator.ValidationError as e:
                # we have an error
                self.error = True

                # get error doc data
                error_documentation = e.get_error_doc()

                if error_documentation not in self.error_documentations and error_documentation is not None:
                    self.error_documentations.append(error_documentation)


class BrandTextInput(miru.TextInput):

    def __init__(self, check=None, check_args=None, prev_values=None, **kwargs):

        if prev_values:
            prev_value = prev_values.get(kwargs.get("custom_id"))

        else:
            prev_value = None

        kwargs["required"] = kwargs.get("required", True)

        super().__init__(
            value=prev_value,
            **kwargs
        )

        self.check = check
        self.check_args = check_args

    async def run_check(self):

        if self.check and self.check_args:

            # if it's a tuple unpack
            if isinstance(self.check_args, tuple):
                return await self.check(self.value, *self.check_args)

            else:
                return await self.check(self.value, self.check_args)

        # if no args just pass in a value
        elif self.check:
            return await self.check(self.value)

        # return the value if no checks
        else:
            return self.value


class Apple(Brand):

    def __init__(self):
        super(Apple, self).__init__()
        self.user_input = UserInput()
        self.title = "Apple"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=20
            )
        ).add_item(
            BrandTextInput(
                label="Date of purchase (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }

        return product

    async def generate_email(self, product, email):
        template = self.get_template("apple", self.spoof)
        user_input = self.user_input.validated

        total = user_input["shipping"] + user_input["price"]
        total = f"{total:.2f}"
        shipping = f"{user_input['shipping']:.2f}"

        order_number = f"W{randint(1231486486, 9813484886)}"

        replacement_values = {

            "ADDRESS1": user_input["name"],
            "ADDRESS2": user_input["shipping_addr"][0],
            "ADDRESS3": user_input["shipping_addr"][1],
            "ADDRESS4": user_input["shipping_addr"][2],
            "ADDRESS5": user_input["shipping_addr"][3],

            "BILLING1": user_input["name"],
            "BILLING2": user_input["shipping_addr"][0],
            "BILLING3": user_input["shipping_addr"][1],
            "BILLING4": user_input["shipping_addr"][2],
            "BILLING5": user_input["shipping_addr"][3],

            "PRODUCT_IMAGE": product["image"],
            "PRODUCT_NAME": product["product_name"],
            "SHIPPING": f"{user_input['currency']}{shipping}",
            "PRODUCT_PRICE": f"{user_input['currency']}{user_input['price']:.2f}",
            "TOTAL": f"{user_input['currency']}{total}",
            "ORDERNUMBER": order_number,
            "EMAIL": email,
            "SPOOF_DATE": self.get_spoof_date(user_input["date"]),
            "DATE": user_input["date"],
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Applе Storе",
            subject=f"We're processing your order {order_number}",
            spoofed_email="noreply@apple.com"
        )


class StockX(Brand):

    def __init__(self):
        super(StockX, self).__init__()
        self.user_input = UserInput()
        self.title = "StockX"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Fee",
                custom_id="fee",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Date of purchase (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        ).add_item(
            BrandTextInput(
                label="Condition New / Used",
                custom_id="condition",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.condition,
                check_args=(["new", "used"])
            )
        ).add_item(
            BrandTextInput(
                label="Size (can be left blank)",
                custom_id="size",
                prev_values=self.user_input.values,
                required=False,
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Product Style Id",
                custom_id="style",
                prev_values=self.user_input.values,
                required=False
            )
        )
        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)

        product = {
            "product_name": self.user_input.validated.get("name"),
            "image": self.user_input.validated.get("image"),
            "size": self.user_input.validated.get("size"),
            "style_id": self.user_input.validated.get("style"),
            "options": {
                "Delivered": {
                    "order_status": "delivered"
                },
                "Ordered": {
                    "order_status": "ordered"
                },
                "Verified": {
                    "order_status": "verified"
                }
            }
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template(f"stockx_new_{product['order_status']}", self.spoof)

        total = utils.format_price(user_input["price"] + user_input["fee"] + user_input["shipping"])
        price = utils.format_price(user_input["price"])

        default_receipt = BeautifulSoup(template, 'html.parser')

        li_elements = default_receipt.find_all("li")

        for li in li_elements:
            if "STYLE_ID" in li.text and product["style_id"]:
                li.string = f"Style ID: {product['style_id']}"

            if "STYLE_ID" in li.text and not product["style_id"]:
                li.extract()

            if "SIZE" in li.text:
                if not user_input["size"]:
                    li.extract()

                li.string = f"Size: {user_input['size']}"
                break

        date_obj = datetime.strptime(user_input["date"], "%m/%d/%Y")

        try:
            date = date_obj.strftime("%-d %B %Y").lstrip("0")
        except ValueError:
            date = date_obj.strftime("%d %B %Y").lstrip("0")

        replacement_values = {
            "PRODUCT_IMAGE": product["image"],
            "PRODUCT_NAME": product["product_name"],
            "ORDER_NUMBER": f"525{randint(15681, 98438)} - 314{randint(15681, 98438)}",
            "DATE": date,
            "CONDITION": user_input["condition"].capitalize(),
            "TOTAL": f"{user_input['currency']}{total}",
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:.2f}",
            "PRICE": f"{user_input['currency']}{price}",
            "FEE": f"{user_input['currency']}{user_input['fee']:.2f}",
        }

        template = default_receipt.prettify()
        for key, value in replacement_values.items():
            template = template.replace(key, str(value))

        if product['order_status'].lower() == "delivered":
            subject = f"🎉Order Delivered: {product['product_name']}"

        elif product['order_status'].lower() == "verified":
            subject = f"✅ Order Verified & Shipped: {product['product_name']}"

        else:
            subject = f"👍 Order Confirmed: {product['product_name']}"

        if user_input['size']: subject += f" (Size {product['size']})"

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="StockX",
            subject=subject,
            spoofed_email="noreply@Տtock-x.com"
        )


class Goat(Brand):

    def __init__(self):
        super(Goat, self).__init__()
        self.user_input = UserInput()
        self.title = "GOAT"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                check=input_validator.UserDataValidator.url,
                prev_values=self.user_input.values,
                check_args=("goat.com/", "goat_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "£", "$"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):

        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Product Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Condition New / Used",
                custom_id="condition",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.condition,
                check_args=["new", "used"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        headers = {
            'x-px-authorization': '3',
            'accept': 'application/json',
            'authorization': 'Token token=""',
            'accept-language': 'en-GB,en;q=0.9',
            'x-emb-st': '1691934124434',
            'user-agent': 'GOAT/2.62.0 (iPhone; iOS 16.6; Scale/2.00) Locale/en',
            'x-emb-id': 'A131256965044D838D97E9AEC3CC32DE',
            'x-px-original-token': '3:7b9f8feffc454bb265869bb69319201a10c0733ded5f64415904867ca6015448'
                                   ':V3kOFKugd0IYEzhYfgTK4QOh8dWCzZH04C4uoGYEfOekVmjMvCYLle7yVImUv8bSOo'
                                   'VChlY3FPELVmFZLboPxA==:1000:V6naWWAGfhIA54bPIFXyWPSpd7e9WmoWghqXoB1'
                                   'xwiAb0TVePEULt5nHoZFhWkpg1E4ZjMtwt1N9yfV2HCYOklHUqUy+oaAlYkACXQLwqsD'
                                   '21d70W55yb0UY9qHQHxY9zQcr6th//3ckUVLU/v1yWhZt/GV9jNyf6EesLG9fw+gqMWP'
                                   'hrpi8bDT1j5eeTR9BLmWMqrY3hmQSYRc9C7K5pQ==',
        }

        scraped_db = database.ScrapedWebLink(self.user_input.validated.get("url"))
        goat_data = await scraped_db.get_scraped_content()

        if not goat_data:

            parsed_url = urlparse(self.user_input.validated.get("url"))
            url_parts = parsed_url.path.split('/')
            last_part = url_parts[-1]

            if not last_part:
                last_part = url_parts[-2]

            try:

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(
                            url=f'https://www.goat.com/api/v1/product_templates/{last_part}/show_v2',
                            headers=headers
                    ) as response:
                        if response.status != 200:
                            raise utils.GenerationError("goat_url")

                        goat_data = await response.json()

            except Exception:
                raise utils.GenerationError("goat_url")

            asyncio.create_task(
                database.ScrapedWebLink(self.user_input.validated.get("url")).save_scraped_content(
                    content=goat_data,
                    title=self.title
                ))
        else:
            goat_data = json.loads(goat_data)

        if not goat_data.get("brandName"):
            raise utils.GenerationError("goat_url")

        product = {
            "product_name": goat_data.get("name"),
            "brand": goat_data.get("brandName"),
            "image": goat_data.get("gridPictureUrl"),
            "product_id": goat_data.get("sku"),
            "options": {
                "Shoe": {
                    "product_type": "shoe"
                },
                "Other": {
                    "product_type": "other"
                }
            }
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template(f"goat", self.spoof)

        total = user_input["price"] + user_input["shipping"]

        size_types = {"$": "US", "€": "EU", "£": "UK"}
        size_type = size_types.get(user_input["currency"])
        order_number = randint(125486684, 895481384)

        if user_input["size"]:
            product_name = f"{product['product_name']} – SIZE {size_type} {user_input['size']}"

        else:
            product_name = user_input["size"]

        packaging = "BOX"
        product_type = "shoe"
        if product['product_type'].lower() != "shoe":
            packaging = "packaging"
            product_type = " "

        replacement_values = {
            "ADDRESS1": user_input["shipping_addr"][0],
            "ADDRESS2": user_input["shipping_addr"][1],
            "ADDRESS3": user_input["shipping_addr"][2],
            "ADDRESS4": user_input["shipping_addr"][3],

            "PRODUCT_NAME": f"{product_name}",
            "BRAND": product["brand"],
            "PRODUCT_ID": product["product_id"],
            "SUBTOTAL": f"{user_input['currency']}{user_input['price']:.2f}",
            "PRODUCTNAME": product['product_name'],
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:.2f}",
            "TOTAL": f"{user_input['currency']}{total:.2f}",
            "PRODUCT_CONDITION": user_input["condition"],
            "PRODUCT_TYPE": product_type,
            "ORDERNUMBER": f"{order_number}",

            "CARD_END": f"{randint(1153, 9671)}",
            "PRODUCT_IMAGE": product["image"],
            "PRODUCT_PACKAGING": packaging,
            "WHOLE_NAME": user_input["name"],
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="GOAT",
            subject=f"Your GOAT order #{order_number}",
            spoofed_email="info@goat.com"
        )


class Farfetch(Brand):

    def __init__(self):
        super(Farfetch, self).__init__()
        self.user_input = UserInput()
        self.title = "Farfetch"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("farfetch.com/", "farfetch_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )
        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Product Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Date of expected delivery (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. City & Zipcode\n2. Street",
                check=input_validator.UserDataValidator.address,
                check_args=2
            )
        )

        return modal

    async def scrape_web(self) -> dict:

        headers = {
            "Host": "www.farfetch.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "sk,cs;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.farfetch.com/sk/stories/men/gift-guide-fw23",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "TE": "trailers"
        }

        try:
            data = await self.fetch_web(headers=headers)
        except Exception:
            raise utils.GenerationError("farfetch_url")

        farfetch_data = BeautifulSoup(data, 'html.parser')

        brand = farfetch_data.find(class_="ltr-183yg4m-Body-Heading-HeadingBold e1h8dali1").text
        name = farfetch_data.find(class_="ltr-13ze6d5-Body efhm1m90").text
        image_tags = farfetch_data.find_all(class_="ltr-1w2up3s")
        image = image_tags[0]["src"]

        product = {
            "product_name": name,
            "brand": brand,
            "image": image,
        }
        return product

    async def generate_email(self, product, email):

        from string import ascii_uppercase

        user_input = self.user_input.validated
        template = self.get_template(f"farfetch", self.spoof)

        price = f"{user_input['price']:,.2f}"
        order_number = ''.join(choice(ascii_uppercase) for _ in range(6))

        replacement_values = {
            "ADDRESS1": user_input['name'].split(" ")[0],
            "ADDRESS2": user_input['shipping_addr'][0],
            "ADDRESS3": user_input['shipping_addr'][1],

            "PRICE": f"{user_input['currency']}{str(price)}",
            "FULLNAME": product['product_name'],
            "ORDERNUMBER": order_number,
            "FIRSTNAME": user_input['name'].split(" ")[0],
            "PRODUCT_IMAGE": product["image"],
            "BRAND": product["brand"],
            "DELIVERY": user_input["date"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="FARFETCH",
            subject=f"Your order will be with you soon",
            spoofed_email="noreply@farfetch.com"
        )


class LouisVuitton(Brand):

    def __init__(self):
        super(LouisVuitton, self).__init__()
        self.user_input = UserInput()
        self.title = "LouisVuitton"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Product Type",
                custom_id="product_type",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        )
        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                check=input_validator.UserDataValidator.name,
                prev_values=self.user_input.values,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder3,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder3,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        )
        return modal

    async def scrape_web(self) -> dict:
        # url = self.user_input.validated.get("url")
        #
        # api_keys = ["b977081c43cd5596777d032a221b5967", "e6f88d0d3e2676bea4dbd465a82d4cc9", "348d3d1f97b8423f91eca526da4a67a7"]
        # payload = {'api_key': "b977081c43cd5596777d032a221b5967",
        #            'url': f'{url}', 'country_code': 'eu',
        #            'device_type': 'desktop'}
        #
        # try:
        #     async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        #         async with session.post("https://api.scraperapi.com/", params=payload) as response:
        #             data = await response.text(encoding="utf-8")
        #
        #             if response.status != 200:
        #                 raise utils.GenerationError("lv_url")
        #
        # except Exception as e:
        #     raise utils.GenerationError("lv_url")
        #
        #
        # lv_data = BeautifulSoup(data, 'html.parser')
        # image_tags = lv_data.find_all('img', class_='lv-smart-picture__object')
        # name = lv_data.find(class_="lv-product__name heading-s").text
        # footer_breadcrumbs = lv_data.find_all("li", class_="lv-footer-breadcrumb__item")
        #
        # image_links = [img['data-srcset'] for img in image_tags if 'data-srcset' in img.attrs]
        # image = None
        #
        # for links in image_links:
        #     for link in links.split(","):
        #
        #         if "Front" in link:
        #             image = link.split(" ")[0]
        #             break
        #
        #         elif "Side" in link:
        #             image = link.split(" ")[0]
        #             break
        #     else:
        #         continue
        #     break
        #
        # if image is None:
        #     raise utils.GenerationError("lv_url")
        #
        # reference = footer_breadcrumbs[len(footer_breadcrumbs) - 3].text

        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
            "reference": self.user_input.validated["product_type"]
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("lv", self.spoof)

        price = f"{user_input['price']:,.2f}"

        country = {"$": "us", "€": "eu", "£": "uk"}.get(user_input['currency'])
        phone_number = {"$": "+1.866.VUITTON", "€": "1300 582 827", "£": "+44 207 998 6286"}.get(user_input["currency"])

        replacement_values = {
            "SHIPPING_ADDRESS1": user_input["name"],
            "SHIPPING_ADDRESS2": user_input["shipping_addr"][0],
            "SHIPPING_ADDRESS3": user_input["shipping_addr"][1],
            "SHIPPING_ADDRESS4": user_input["shipping_addr"][2],

            "BILLING_ADDRESS1": user_input["name"],
            "BILLING_ADDRESS2": user_input["billing_addr"][0],
            "BILLING_ADDRESS3": user_input["billing_addr"][1],
            "BILLING_ADDRESS4": user_input["billing_addr"][2],

            "PRODUCT_NAME": product["product_name"],
            "REFERENCE": product["reference"],
            "PRODUCT_PRICE": f"{user_input['currency']}{str(price)}",
            "PRODUCTNAME": product["product_name"],
            "CARTTOTAL": str(price),
            "ORDERNUMBER": f"nv{randint(125486684, 895481384)}",
            "FIRSTNAME": user_input["name"].split(" ")[0],
            "COUNTRY": country,
            "CURRENCY": user_input["currency"],
            "PHONE_NUMBER": phone_number,
            "PRODUCT_IMAGE": product["image"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Louis Vuitton",
            subject=f"Your Louis Vuitton Order Has been Shipped",
            spoofed_email=f"noreply@louisvuitton.{country}.com"
        )


class Nike(Brand):

    def __init__(self):
        super(Nike, self).__init__()
        self.user_input = UserInput()
        self.title = "Nike"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Date of delivery (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        ).add_item(
            BrandTextInput(
                label="Date of order (M/D/YYYY)",
                custom_id="order_date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        )
        return modal

    async def scrape_web(self) -> dict:
        # data = await self.fetch_web()
        # nike_data = BeautifulSoup(data, 'html.parser')
        #
        # image = None
        # try:
        #     title_container = nike_data.find(id='title-container').find("h1")
        #     name = title_container.text.strip() if title_container else None
        #
        # except AttributeError:
        #
        #     try:
        #         name1 = nike_data.find(class_="headline-5=small").text
        #         name2 = nike_data.find(class_="headline-2").text
        #
        #     except AttributeError:
        #
        #         name1 = nike_data.find(class_="headline-5 pb3-sm").text
        #         name2 = nike_data.find(class_="headline-1 pb3-sm").text
        #
        #     name = f"{name1.strip()} {name2.strip()}"
        #
        #     image = nike_data.find('meta', property='og:image')
        #     image = image['content'] if image else None
        #
        # if not image or not name:
        #     raise utils.GenerationError("nike_url")

        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("nike", self.spoof)

        total = user_input["price"] + 10.46
        size_country = {"$": "US", "€": "EU", "£": "UK"}.get(user_input["currency"])
        order_number = f"C{randint(12348612348, 98134861238)}"

        replacement_values = {

            "WHOLE_NAME": user_input["name"],
            "FIRSTNAME": user_input["name"].split(" ")[0],
            "ADDRESS1": user_input["shipping_addr"][0],
            "ADDRESS2": user_input["shipping_addr"][1],
            "ADDRESS3": user_input["shipping_addr"][2],

            "PRODUCT_NAME": product["product_name"],
            "SIZE": f"{size_country} {user_input['size']}",
            "PRICE": f"{user_input['currency']}{user_input['price']:.2f}",
            "TOTAL": f"{user_input['currency']}{total:.2f}",
            "CURRENCY": user_input['currency'],
            "ORDER_NUMBER": order_number,
            "PRODUCT_IMAGE": product["image"],
            "CARD_END": f"{randint(1346, 9826)}",
            "ORDER_DATE": datetime.strptime(user_input['order_date'], "%m/%d/%Y").strftime("%b %d, %Y"),
            "DELIVERY_DATE": datetime.strptime(user_input['date'], "%m/%d/%Y").strftime("%b %d, %Y")
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Nike.com",
            subject=f"Thank You for Your Order (#{order_number})",
            spoofed_email="noreply@nike.com"
        )


class Bape(Brand):

    def __init__(self):
        super(Bape, self).__init__()
        self.user_input = UserInput()
        self.title = "Bape"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=(".bape.com/", "bape_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£,zł)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£", "zł"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Tax",
                custom_id="tax",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        try:
            data = await self.fetch_web()

        except Exception:
            raise utils.GenerationError("url_bape")

        bape_data = BeautifulSoup(data, 'html.parser')
        name = bape_data.find(class_="product__section-title").text
        name = name.strip()
        image = bape_data.find(class_="product__image")["src"]
        if image.startswith('//'): image = image[2:]
        style = bape_data.find(class_="swatches__option-value").text

        if not image or not name or not style:
            raise utils.GenerationError("url_bape")

        product = {
            "product_name": name,
            "image": image,
            "style": style
        }
        return product

    async def generate_email(self, product, email):

        user_input = self.user_input.validated
        template = self.get_template("bape", self.spoof)

        total = user_input["shipping"] + user_input["price"] + user_input["tax"]
        total = f"{total:.2f}"

        order_number = f"LE{randint(123, 739)}-{randint(11, 99)}-{randint(15423, 95874)}"

        replacement_values = {

            "ADDRESS1": user_input["name"],
            "ADDRESS2": user_input["shipping_addr"][0],
            "ADDRESS3": user_input["shipping_addr"][1],
            "ADDRESS4": user_input["shipping_addr"][2],

            "BILLING1": user_input["name"],
            "BILLING2": user_input["billing_addr"][0],
            "BILLING3": user_input["billing_addr"][1],
            "BILLING4": user_input["billing_addr"][2],

            "PRODUCT_NAME": product["product_name"],
            "SIZE": user_input["size"],
            "STYLE": product["style"],
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:.2f}",
            "PRICE": f"{user_input['currency']}{user_input['price']:.2f}",
            "TOTAL": f"{user_input['currency']}{total}",
            "CURRENCY_STR": {"$": "USD", "€": "EUR", "£": "GBP", "zł": "PLN"}.get(user_input['currency']),
            "ORDER_NUMBER": order_number,
            "IMAGE": product["image"],
            "TAXES": f"{user_input['currency']}{user_input['tax']:.2f}",
            "CARD_END": f"{randint(1346, 9826)}",
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="BAPE",
            subject=f"Order #{order_number} confirmed",
            spoofed_email="noreply@bape.com"
        )


class Moncler(Brand):

    def __init__(self):
        super(Moncler, self).__init__()
        self.user_input = UserInput()
        self.title = "Moncler"

    async def get_step_one(self):

        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("moncler.com/", "moncler_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£,zł)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£", "zł"]
            )
        ).add_item(
            BrandTextInput(
                label="Date of order (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3
            )
        )

        return modal

    async def scrape_web(self) -> dict:

        def extract_id_from_url(og_url):
            parsed_url = urlparse(og_url)
            path = parsed_url.path

            if ".html" in path:
                index = path.index(".html")
                if index >= 20:
                    return path[index - 20:index]
                else:
                    return path[:index]
            else:
                raise utils.GenerationError("moncler_url")

        headers = {
            "authority": "www.moncler.com",
            "accept": "application/json",
            "accept-language": "sk-SK,sk;q=0.9,en-SK;q=0.8,en;q=0.7,cs;q=0.6,en-US;q=0.5",
            "baggage": "sentry-environment=moncweb-prod,sentry-release=13.7.2-20231122.932,"
                       "sentry-public_key=d4fd99cefa4741af819754d0a79d3d82,"
                       "sentry-trace_id=64c092b56ad9470388cff14bbef31ce0,sentry-sample_rate=0.1",
            "device": "undefined",
            "referer": "https://www.moncler.com/en-sk/women/shoes/boots/trailgrip-apres-boots-beige"
                       "-I209B4H00080M323426B.html",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sentry-trace": "64c092b56ad9470388cff14bbef31ce0-a743b69c4eaa8dbe-0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/119.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

        product_id = extract_id_from_url(self.user_input.validated["url"])
        url = f"https://www.moncler.com/on/demandware.store/Sites-MonclerEU-Site/en_SK/ProductApi-Product?pid={product_id}"
        try:
            data = await self.fetch_web(headers=headers, url=url)
        except Exception:
            raise utils.GenerationError("moncler_url")

        moncler_data = json.loads(data)
        name = moncler_data.get("productName")
        color = moncler_data.get("variationAttributes")[0]["displayValue"]
        image = moncler_data.get("pageMetaTags").get("og:image")

        product = {
            "product_name": name,
            "image": image,
            "color": color
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("moncler", self.spoof)

        date_object = datetime.strptime(user_input['date'], "%m/%d/%Y")
        estimated_date = date_object + timedelta(days=7)
        estimated_date = estimated_date.strftime("%d %B %Y")
        order_date = date_object.strftime("%d %B %Y")
        order_number = f"{randint(123459123459, 928647928647)}"

        replacement_values = {

            "ADDRESS1": user_input["name"],
            "ADDRESS2": user_input["shipping_addr"][0],
            "ADDRESS3": user_input["shipping_addr"][1],
            "ADDRESS4": user_input["shipping_addr"][2],

            "BILLING1": user_input["name"],
            "BILLING2": user_input["billing_addr"][0],
            "BILLING3": user_input["billing_addr"][1],
            "BILLING4": user_input["billing_addr"][2],
            "DATE": order_date,

            "CARD_END": str(randint(1234, 9568)),
            "ESTIMATED_DELIVERY": estimated_date,
            "FIRST_NAME": user_input["name"].split(" ")[0],
            "PRODUCT_NAME": product["product_name"],
            "SIZE": user_input["size"],
            "COLOUR": product["color"],
            "TOTAL": f"{user_input['currency']}{user_input['price']:,.2f}",
            "ORDER_NUMBER": order_number,
            "IMAGE": product["image"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Moncler Online Store",
            subject=f"Thank you for your order",
            spoofed_email="support@moncler-shop.com"
        )


class OffWhite(Brand):

    def __init__(self):
        super(OffWhite, self).__init__()
        self.user_input = UserInput()
        self.title = "OffWhite"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£,zł)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£", "zł"]
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Cost",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£,zł)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["€", "$", "£", "zł"]
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)

        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("offwhite", self.spoof)

        characters = string.ascii_uppercase + string.digits
        order_number = ''.join(choice(characters) for _ in range(6))
        total = user_input["price"] + user_input["shipping"]

        replacement_values = {
            "FIRST_NAME": user_input["name"].split(" ")[0],
            "PRODUCT_NAME": product["product_name"],
            "R_SHIPPING": f"{user_input['currency']}{user_input['price']:,.2f}",
            "R_TOTAL": f"{user_input['currency']}{total},.2f",
            "ORDER_NUMBER": order_number,
            "PRODUCT_PRICE": f"{user_input['currency']}{user_input['price']:,.2f}",
            "PRODUCT_IMAGE": product["image"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Off-White",
            subject=f"Thank you for placing your order"
        )


class Ebay(Brand):

    def __init__(self):
        super(Ebay, self).__init__()
        self.user_input = UserInput()
        self.title = "Ebay"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("ebay.com/", "ebay_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Date of delivery (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Seller Name",
                custom_id="seller_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Your name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        ).add_item(
            BrandTextInput(
                label="Product Reference (below the product)",
                custom_id="product_reference",
                prev_values=self.user_input.values,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        url = self.user_input.validated.get("url")

        try:
            data = await self.fetch_web(url=url, headers={})
        except Exception:
            raise utils.GenerationError("ebay_url")

        ebay_data = BeautifulSoup(data, 'html.parser')
        name = ebay_data.find("span", class_="ux-textspans ux-textspans--BOLD").text
        image = ebay_data.find("div", class_="ux-image-carousel-item").find("img")["src"]

        product = {
            "product_name": name,
            "image": image,
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("ebay", self.spoof)

        part1 = randint(10, 99)
        part2 = randint(10000, 99999)
        part3 = randint(10000, 99999)
        order_number = f"{part1}-{part2}-{part3}"

        total = user_input['price'] + user_input['shipping']

        replacement_values = {

            "ADDRESS0": user_input["shipping_addr"][0],
            "ADDRESS1": user_input["shipping_addr"][1],
            "ADDRESS2": user_input["shipping_addr"][2],
            "ADDRESS3": user_input["shipping_addr"][3],

            "DATE": user_input["date"],

            "PRODUCT_REFERENCE": user_input["product_reference"],
            "FIRST_NAME": user_input["name"].split(" ")[0],
            "SELLER_NAME": user_input["seller_name"],
            "PRODUCT_NAME": product["product_name"],
            "PRODUCT_PRICE": f"{user_input['currency']}{user_input['price']:,.2f}",
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:,.2f}",
            "TOTAL": f"{user_input['currency']}{total:,.2f}",
            "ORDER_NUMBER": order_number,
            "PRODUCT_IMAGE": product["image"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Ebay",
            subject=f"Your purchase is confirmed"
        )


class Prada(Brand):

    def __init__(self):
        super(Prada, self).__init__()
        self.user_input = UserInput()
        self.title = "Prada"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("prada.com/", "prada_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Tax",
                custom_id="tax",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Color",
                custom_id="color",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        url = self.user_input.validated.get("url")

        try:
            data = await self.fetch_web(url=url)
        except Exception:
            raise utils.GenerationError("prada_url")

        prada_data = BeautifulSoup(data, 'html.parser')
        image = prada_data.find("img", class_="pdp-product-img")['srcset'].split(',')[0].strip().split(' ')[0]
        name = prada_data.find("h1", class_="text-title-big").text

        ul_tag = prada_data.find('ul', class_='list-disc')
        first_li = ul_tag.find('li')
        product_code_text = first_li.get_text()
        product_code = product_code_text.split(': ')[1]

        product = {
            "product_name": name,
            "image": image,
            "product_code": product_code
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("prada", self.spoof)

        letters = ''.join(choices(string.ascii_uppercase, k=4))
        numbers = ''.join(choices(string.digits, k=8))
        order_number = letters + numbers

        total = user_input['price'] + user_input['shipping'] + user_input['tax']

        replacement_values = {

            "ADDRESS1": user_input["shipping_addr"][0],
            "ADDRESS2": user_input["shipping_addr"][1],
            "ADDRESS3": user_input["shipping_addr"][2],
            "ADDRESS4": user_input["shipping_addr"][3],

            "PRODUCT_CODE": product["product_code"],
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_COLOR": user_input["color"],
            "SIZE": user_input["size"],
            "PRODUCT_NAME": product["product_name"],
            "PRICE": f"{user_input['currency']}{user_input['price']:,.2f}",
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:,.2f}",
            "TOTAL": f"{user_input['currency']}{total:,.2f}",
            "TAX": f"{user_input['currency']}{user_input['tax']:,.2f}",
            "ORDER_NUMBER": order_number,
            "PRODUCT_IMAGE": product["image"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Prada",
            subject=f"Prada - Order acknowledgement - {order_number}",
            spoofed_email="noreply@prada.com"
        )


class Balenciaga(Brand):

    def __init__(self):
        super(Balenciaga, self).__init__()
        self.user_input = UserInput()
        self.title = "Balenciaga"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("balenciaga.com/", "balenciaga_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Fee",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3,
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder2,
                check=input_validator.UserDataValidator.address,
                check_args=3,
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        url = self.user_input.validated.get("url")

        try:
            data = await self.fetch_web(url=url)
        except Exception:
            raise utils.GenerationError("balenciaga_url")

        balenciaga_data = BeautifulSoup(data, 'html.parser')

        product_name = balenciaga_data.find(class_="c-product__name").string
        json_script = balenciaga_data.find('script', {'type': 'application/ld+json', 'defer': ''})
        json_data = json.loads(json_script.string)
        image = json_data.get("image")
        color = json_data.get("color")

        product = {
            "product_name": product_name,
            "image": image,
            "color": color
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("balenciaga", self.spoof)

        order_number = [choice(string.ascii_uppercase) for _ in range(9)]
        order_number[randint(0, 4)] = randint(0, 9)
        order_number.extend([randint(0, 9) for _ in range(9)])
        order_number = "".join([str(char) for char in order_number])

        total = user_input["shipping"] + user_input["price"]

        replacement_values = {
            "ADDRESS1": user_input["name"],
            "ADDRESS2": user_input["shipping_addr"][0],
            "ADDRESS3": user_input["shipping_addr"][1],
            "ADDRESS4": user_input["shipping_addr"][2],

            "BILLING1": user_input["name"],
            "BILLING2": user_input["billing_addr"][0],
            "BILLING3": user_input["billing_addr"][1],
            "BILLING4": user_input["billing_addr"][2],

            "PRODUCT_COLOUR": product["color"],
            "PRODUCT_NAME": product["product_name"],
            "FIRSTNAME": user_input["name"].split(" ")[0],
            "PRODUCT_PRICE": f"{user_input['currency']} {user_input['price']:,.2f}",
            "PRODUCT_TOTAL": f"{user_input['currency']} {total:,.2f}",
            "ORDERNUMBER": order_number,
            "PRODUCT_IMAGE": product["image"],
            "SHIPPING_F": f"{user_input['currency']} {user_input['shipping']:,.2f}"
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Balenciaga",
            subject="Your Balenciaga Order Registration",
            spoofed_email="noreply@balenciaga.com"
        )


class Supreme(Brand):

    def __init__(self):
        super(Supreme, self).__init__()
        self.user_input = UserInput()
        self.title = "Supreme"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Fee",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Vat",
                custom_id="vat",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Style",
                custom_id="style",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Date of order (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check_args=input_validator.UserDataValidator.date
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        )

        return modal

    async def scrape_web(self) -> dict:

        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "style": self.user_input.validated["style"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("supreme", self.spoof)

        total = user_input['shipping'] + user_input['vat'] + user_input['price']
        date_obj = datetime.strptime(user_input["date"], "%m/%d/%Y")
        try:
            date = date_obj.strftime("%-d %B %Y").lstrip("0")
        except ValueError:
            date = date_obj.strftime("%d %B %Y").lstrip("0")

        replacement_values = {
            "WHOLENAME": user_input["name"],
            "ORDERNUMBER": f"{randint(1813942948648, 9459995699998)}",
            "PRODUCTSTYLE": product["style"],
            "PRODUCTSIZE": user_input["size"],
            "PRODUCTPRICE": f"{user_input['currency']}{user_input['price']:,.2f}",
            "PRODUCTNAME": product["product_name"],
            "CARTTOTAL": f"{user_input['currency']}{user_input['price']:,.2f}",
            "ORDER_TOTAL": f"{user_input['currency']}{total:,.2f}",
            "TIMEDATE": date,
            "ORDERDATE": date,
            "VAT_T": f"{user_input['currency']}{user_input['vat']:,.2f}",
            "SHIPPING": f"{user_input['currency']}{user_input['shipping']:,.2f}",
            "COUNTRY_CODE": {"€": "eu", "$": "us", "£": "uk"}.get(user_input['currency'])
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Supreme",
            subject="online shop order",
            spoofed_email="london@supremenewyork.com"
        )


class Dior(Brand):

    def __init__(self):
        super(Dior, self).__init__()
        self.user_input = UserInput()
        self.title = "Dior"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Tax",
                custom_id="tax",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder1,
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("dior", self.spoof)

        order_number = f"{randint(138652867, 898911983)}"

        total = user_input["price"] + user_input["tax"]

        replacement_values = {
            "SHIPPING1": user_input['shipping_addr'][0],
            "SHIPPING2": user_input['shipping_addr'][1],
            "SHIPPING3": user_input['shipping_addr'][2],
            "SHIPPING4": user_input['shipping_addr'][3],

            "BILLING1": user_input['billing_addr'][0],
            "BILLING2": user_input['billing_addr'][1],
            "BILLING3": user_input['billing_addr'][2],
            "BILLING4": user_input['billing_addr'][3],

            "PRICE": f"{user_input['currency']} {user_input['price']:,.2f}",
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_NAME": product["product_name"],
            "ORDER_NUMBER": order_number,
            "PRODUCT_IMAGE": product["image"],
            "TOTAL": f"{user_input['currency']} {total:,.2f}",
            "TAXES": f"{user_input['currency']} {user_input['tax']:,.2f}",
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Dior",
            subject="Your order confirmation",
            spoofed_email="noreply@diorstore.com"
        )


class Amazon(Brand):

    def __init__(self):
        super(Amazon, self).__init__()
        self.user_input = UserInput()
        self.title = "Amazon"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. City\n2. State",
                check=input_validator.UserDataValidator.address,
                check_args=2,
            )
        ).add_item(
            BrandTextInput(
                label="Est. Arrival Date (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        recommended_products = [
            ["https://m.media-amazon.com/images/I/61C6+EtzxfL._AC_UY218_.jpg",
             "14 ProMAX Unlocked Cell Phone.."],
            ["https://m.media-amazon.com/images/I/51M3ig2cbHL._AC_UL320_.jpg",
             "Jean Paul Gaultier Le Male Elixir..."],
            ["https://m.media-amazon.com/images/I/41roAPXkT5L._AC_SY450_.jpg",
             "Apple AirPods (2nd Gen) Wireless Ear Buds..."],
        ]

        recommended_products = sample(recommended_products, 2)

        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
            "recommended_products": recommended_products
        }

        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("amazon", self.spoof)

        order_number = f"{randint(111, 999)}-{randint(1386528, 8989119)}-{randint(1386528, 8989119)}"

        date_obj = datetime.strptime(user_input["date"], "%m/%d/%Y")
        date = date_obj.strftime("%A, %B ") + str(date_obj.day)

        replacement_values = {
            "ADDRESS1": user_input['shipping_addr'][0],
            "ADDRESS2": user_input['shipping_addr'][1],

            "PRICE": f"{user_input['currency']} {user_input['price']:,.2f}",
            "FIRST_NAME": user_input["name"].split(" ")[0],
            "PRODUCT_NAME": product["product_name"],
            "ORDER_NUMBER": order_number,
            "NAME": user_input["name"],
            "IMAGE": product["image"],
            "TOTAL": f"{user_input['currency']} {user_input['price']:,.2f}",
            "ARRIVAL_DATE": date,
            "R_PRODUCT_NAM2": product["recommended_products"][0][1],
            "R_PRODUCT_NAM3": product["recommended_products"][1][1],
            "R_IMG2": product["recommended_products"][0][0],
            "R_IMG3": product["recommended_products"][1][0],
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Amazon",
            subject=f"Your Amazon.com order of {product['product_name'][:30]}...",
            spoofed_email="auto-confirm@amazonn.com"
        )


class Grailed(Brand):

    def __init__(self):
        super(Grailed, self).__init__()
        self.user_input = UserInput()
        self.title = "Grailed"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Product Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Product Brand",
                custom_id="brand",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Tax",
                custom_id="tax",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Seller Country",
                custom_id="seller_location",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder=self.address_placeholder3,
                check=input_validator.UserDataValidator.address,
                check_args=3,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("grailed", self.spoof)

        total = user_input["price"] + user_input["tax"]

        replacement_values = {
            "SHIPPING1": user_input['shipping_addr'][0],
            "SHIPPING2": user_input['shipping_addr'][1],
            "SHIPPING3": user_input['shipping_addr'][2],

            "PRICE": f"{user_input['currency']} {user_input['price']:.2f}",
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_NAME": product["product_name"],
            "PRODUCT_IMAGE": product["image"],
            "SIZE": user_input["size"],
            "BRAND": user_input["brand"],
            "PROD_TOTAL": f"{user_input['currency']} {total:.2f}",
            "TAX": f"{user_input['currency']} {user_input['tax']:.2f}",
            "USER_LOCATION": user_input['shipping_addr'][2],
            "SELLER_LOCATION": user_input["seller_location"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Grailed",
            subject="Congrats on your purchase!",
            spoofed_email="noreply@graild.com"
        )


class GrailPoint(Brand):

    def __init__(self):
        super(GrailPoint, self).__init__()
        self.user_input = UserInput()
        self.title = "Grail Point"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Url",
                custom_id="url",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.url,
                check_args=("grailpoint.com/", "grailpoint_url")
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Tax",
                custom_id="tax",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£,zł)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£", "zł"]
            )
        ).add_item(
            BrandTextInput(
                label="Order Date (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. Street\n2. Postal Code & City",
                check=input_validator.UserDataValidator.address,
                check_args=2,
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. Street\n2. Postal Code & City\n3. Phone Number",
                check=input_validator.UserDataValidator.address,
                check_args=3,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        url = self.user_input.validated.get("url")

        try:
            data = await self.fetch_web(url=url)
        except Exception:
            raise utils.GenerationError("grailpoint_url")

        grailpoint_data = BeautifulSoup(data, 'html.parser')
        name = grailpoint_data.find("h1", class_="single-product__title").text
        image = grailpoint_data.find('meta', {'property': 'og:image'}).get("content")

        product = {
            "product_name": name,
            "image": image,
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("grailpoint", self.spoof)

        polish_months = [
            'stycznia',  # January
            'lutego',  # February
            'marca',  # March
            'kwietnia',  # April
            'maja',  # May
            'czerwca',  # June
            'lipca',  # July
            'sierpnia',  # August
            'września',  # September
            'października',  # October
            'listopada',  # November
            'grudnia'  # December
        ]

        order_number = f"{randint(138652, 898911)}"
        total = user_input["price"] + user_input["tax"]
        date_split = user_input["date"].split("/")
        date = f"{polish_months[int(date_split[0])]} {date_split[1]}, {date_split[2]}"

        replacement_values = {
            "SHIPPING1": user_input['shipping_addr'][0],
            "SHIPPING2": user_input['shipping_addr'][1],

            "BILLING1": user_input['billing_addr'][0],
            "BILLING2": user_input['billing_addr'][1],
            "BILLING3": user_input['billing_addr'][2],

            "PRICE": f"{user_input['price']:.2f}",
            "CURRENCY": f"{user_input['currency']}",
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_NAME": product["product_name"],
            "PRODUCT_LINK": user_input["url"],
            "ORDER_NUMBER": order_number,
            "DATE": date,
            "IMAGE": product["image"],
            "TOTAL": f"{total:.2f}",
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Grail Point",
            subject="[Grail Point] Otrzymaliśmy twoje zamówienie!",
            spoofed_email="noreply@grailpoint.com"
        )


class Dyson(Brand):

    def __init__(self):
        super(Dyson, self).__init__()
        self.user_input = UserInput()
        self.title = "Dyson"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Vat",
                custom_id="vat",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Delivery Fee",
                custom_id="delivery",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Shipping Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. Street\n2. City\n3. Zip Code\n4. Country",
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        ).add_item(
            BrandTextInput(
                label="Billing Address",
                custom_id="billing_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. Street\n2. City\n3. Zip Code\n4. Country",
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("dyson", self.spoof)

        total = user_input["price"] + user_input["vat"] + user_input["delivery"]

        order_number = str(randint(1234567890, 9999999999))

        replacement_values = {
            "ADDRESS": user_input['shipping_addr'][0],
            "CITY": user_input['shipping_addr'][1],
            "POSTCODE": user_input['shipping_addr'][2],
            "COUNTRY": user_input['shipping_addr'][3],

            "BILLING1": user_input['billing_addr'][0],
            "BILLING2": user_input['billing_addr'][1],
            "BILLING3": user_input['billing_addr'][2],
            "BILLING4": user_input['billing_addr'][3],

            "PRICE": f"{user_input['currency']}{user_input['price']:,.2f}",
            "ORDER_NUMBER": order_number,
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_NAME": product["product_name"],
            "IMAGE": product["image"],
            "TOTAL": f"{user_input['currency']}{total:,.2f}",
            "DELIVERY": f"{user_input['currency']}{user_input['delivery']:,.2f}",
            "PROD_VAT": f"{user_input['currency']}{user_input['vat']:,.2f}",
            "CURRENCY": user_input['currency']
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Dyson",
            subject=f"Your Dyson order confirmation {order_number}",
            spoofed_email="noreply@dyson.co.uk"
        )

class Sephora(Brand):

    def __init__(self):
        super(Sephora, self).__init__()
        self.user_input = UserInput()
        self.title = "Sephora"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Item Number",
                custom_id="item_number",
                prev_values=self.user_input.values,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Order Date (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("sephora", self.spoof)

        order_number = str(randint(123456789000, 999999999999))
        date_obj = datetime.strptime(user_input["date"], "%m/%d/%Y")
        order_date = date_obj.strftime("%b. %d, %Y")

        replacement_values = {
            "ORDER_NUMBER": f"#{order_number}",
            "FIRST_NAME": user_input["name"].split(" ")[0],
            "PRODUCT_NAME": product["product_name"],
            "PRODUCT_IMAGE": product["image"],
            "ORDER_DATE": order_date,
            "ITEM_NUMBER": user_input["item_number"]
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Sephora",
            subject=f"Get excited: Your order #{order_number} is almost here!",
            spoofed_email="noreply@sephora.org"
        )

class CanadaGoose(Brand):

    def __init__(self):
        super(CanadaGoose, self).__init__()
        self.user_input = UserInput()
        self.title = "CanadaGoose"

    async def get_step_one(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Product Name",
                custom_id="product_name",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Direct Image Link",
                custom_id="image",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.image,
            )
        ).add_item(
            BrandTextInput(
                label="Price",
                custom_id="price",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Currency($,€,£)",
                custom_id="currency",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.currency,
                check_args=["$", "€", "£"]
            )
        ).add_item(
            BrandTextInput(
                label="Shipping",
                custom_id="shipping",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        )

        return modal

    async def get_step_two(self):
        modal = ReceiptModal(self) \
            .add_item(
            BrandTextInput(
                label="Vat",
                custom_id="vat",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.common_value,
            )
        ).add_item(
            BrandTextInput(
                label="Your Name",
                custom_id="name",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.name,
                check_args=30,
            )
        ).add_item(
            BrandTextInput(
                label="Order Date (M/D/YYYY)",
                custom_id="date",
                prev_values=self.user_input.values,
                check=input_validator.UserDataValidator.date,
            )
        ).add_item(
            BrandTextInput(
                label="Color | Size",
                custom_id="size",
                prev_values=self.user_input.values,
            )
        ).add_item(
            BrandTextInput(
                label="Address",
                custom_id="shipping_addr",
                prev_values=self.user_input.values,
                style=hikari.TextInputStyle.PARAGRAPH,
                placeholder="1. Street\n2. City\n3. Zip Code\n4. Country",
                check=input_validator.UserDataValidator.address,
                check_args=4,
            )
        )

        return modal

    async def scrape_web(self) -> dict:
        await asyncio.sleep(1)
        product = {
            "product_name": self.user_input.validated["product_name"],
            "image": self.user_input.validated["image"],
        }
        return product

    async def generate_email(self, product, email):
        user_input = self.user_input.validated
        template = self.get_template("canada_goose", self.spoof)

        invoice_number = str(randint(12345678900012345678, 99999999999912348975))
        order_number = str(randint(111111111, 999999999))
        date_obj = datetime.strptime(user_input["date"], "%m/%d/%Y")
        order_date = date_obj.strftime("%d/%m/%Y")

        subtotal = user_input["shipping"] + user_input["price"]
        total = user_input["shipping"] + user_input["vat"] + user_input["price"]

        replacement_values = {

            "SHIPPING1": user_input["shipping_addr"][0],
            "SHIPPING2": user_input["shipping_addr"][1],
            "SHIPPING3": user_input["shipping_addr"][2],
            "SHIPPING4": user_input["shipping_addr"][3],

            "INVOICE_NUMBER": f"{invoice_number}",
            "ORDER_NUMBER": f"CGGB_{order_number}",
            "WHOLE_NAME": user_input["name"],
            "PRODUCT_NAME": product["product_name"],
            "PRODUCT_IMAGE": product["image"],
            "PROD_COL": user_input["size"],
            "ORDER_DATE": order_date,
            "SHIPPING_PRICE": f"{user_input['currency']}{user_input['shipping']:.2f}",
            "PRODUCT_PRICE": f"{user_input['currency']}{user_input['price']:.2f}",
            "SUBTOTAL_PRICE": f"{user_input['currency']}{subtotal:.2f}",
            "VAT_PRICE": f"{user_input['currency']}{user_input['vat']:.2f}",
            "TOTAL_PRICE": f"{user_input['currency']}{total:.2f}",
            "CARD_NUMBER": f"{randint(1111, 9999)}"
        }

        for key, value in replacement_values.items():
            template = template.replace(key, value)

        await self.send_email(
            to_email=email,
            html_content=template,
            sender_name="Canada Goose",
            subject=f"Your Order Order invoice #{order_number}",
            spoofed_email="noreply@canadagoose.uk.co"
        )

with open("receiptgen/config.json", "r") as file:
    config = json.load(file)
    file.close()

brand_options = {
    "Stockx": [
        StockX,
        hikari.CustomEmoji(id=config['emojis']['stockx'], name="stockx", is_animated=False)
    ],
    "Apple": [
        Apple,
        hikari.CustomEmoji(id=config['emojis']['apple'], name="apple", is_animated=False)
    ],
    "GOAT": [
        Goat,
        hikari.CustomEmoji(id=config['emojis']['goat'], name="goat", is_animated=False)
    ],
    "Farfetch": [
        Farfetch,
        hikari.CustomEmoji(id=config['emojis']['farfetch'], name="farfetch", is_animated=False)
    ],
    "LouisVuitton": [
        LouisVuitton,
        hikari.CustomEmoji(id=config['emojis']['louisvuitton'], name="louisvuitton", is_animated=False)
    ],
    "Nike": [
        Nike,
        hikari.CustomEmoji(id=config['emojis']['nike'], name="nike", is_animated=False)
    ],
    "Bape": [
        Bape,
        hikari.CustomEmoji(id=config['emojis']['bape'], name="bape", is_animated=False)
    ],
    "Moncler": [
        Moncler,
        hikari.CustomEmoji(id=config['emojis']['moncler'], name="moncler", is_animated=False)
    ],
    "Ebay": [
        Ebay,
        hikari.CustomEmoji(id=config['emojis']['ebay'], name="ebay", is_animated=False)
    ],
    "Offwhite": [
        OffWhite,
        hikari.CustomEmoji(id=config['emojis']['offwhite'], name="offwhite", is_animated=False)
    ],
    "Prada": [
        Prada,
        hikari.CustomEmoji(id=config['emojis']['prada'], name="prada", is_animated=False)
    ],
    "Balenciaga": [
        Balenciaga,
        hikari.CustomEmoji(id=config['emojis']['balenciaga'], name="balenciaga", is_animated=False)
    ],
    "Supreme": [
        Supreme,
        hikari.CustomEmoji(id=config['emojis']['supreme'], name="supreme", is_animated=False)
    ],
    "Dior": [
        Dior,
        hikari.CustomEmoji(id=config['emojis']['dior'], name="dior", is_animated=False)
    ],
    "Amazon": [
        Amazon,
        hikari.CustomEmoji(id=config['emojis']['amazon'], name="amazon", is_animated=False)
    ],
    "Grailed": [
        Grailed,
        hikari.CustomEmoji(id=config['emojis']['grailed'], name="grailed", is_animated=False)
    ],
    "GrailPoint": [
        GrailPoint,
        hikari.CustomEmoji(id=config['emojis']['grailpoint'], name="grailpoint", is_animated=False)
    ],
    "Dyson": [
        Dyson,
        hikari.CustomEmoji(id=config['emojis']['dyson'], name="dyson", is_animated=False)
    ],
    "Sephora": [
        Sephora,
        hikari.CustomEmoji(id=config['emojis']['sephora'], name="sephora", is_animated=False)
    ],
    "CanadaGoose": [
        CanadaGoose,
        hikari.CustomEmoji(id=config['emojis']['sephora'], name="sephora", is_animated=False)
    ]
}
