import requests

from receiptgen import utils
import datetime
import aiohttp
import asyncio
from urllib.parse import urlparse


class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


        self.config = utils.get_config()
        self.error = message

    def get_error_doc(self) -> dict:
        error_documentation = self.config["error_docs"].get(self.error)
        return error_documentation


class UserDataValidator:

    @staticmethod
    async def common_value(value: str) -> float:

        try:
            value = float(value)
            return value

        except ValueError:
            raise ValidationError("value")


    @staticmethod
    async def currency(currency: str, currency_types: list[str]) -> str:
        if currency not in currency_types:
            raise ValidationError("currency")

        return currency

    @staticmethod
    async def address(paragraph: str, lines: int) -> list[str]:
        split_paragraph = paragraph.split("\n")
        if len(split_paragraph) != lines:
            raise ValidationError("address")

        return split_paragraph

    @staticmethod
    async def name(name: str, max_length=20) -> str:
        if 2 > len(name) > max_length:
            raise ValidationError("name")

        return name


    @staticmethod
    async def date(date: str) -> str:
        try:
            datetime.datetime.strptime(date, '%m/%d/%Y')
            return date

        except ValueError:
            raise ValidationError("date1")


    @staticmethod
    async def condition(condition: str, conditions: list):

        if condition.lower() not in conditions:
            raise ValidationError("condition")

        return condition

    @staticmethod
    async def url(url: str, base_url: str, brand_url_name):
        if base_url not in url:
            raise ValidationError(brand_url_name)

        return url

    @staticmethod
    async def image(url: str):
        IMAGE_SIGNATURES = {
            b'\xff\xd8\xff': 'jpeg',  # JPEG
            b'\x89PNG\r\n\x1a\n': 'png',  # PNG
            b'GIF87a': 'gif',  # GIF
            b'GIF89a': 'gif',  # GIF
            b'BM': 'bmp',  # BMP
            b'RIFF': 'webp',  # WebP
            b'II*\x00': 'tiff',  # TIFF
            b'MM\x00*': 'tiff',  # TIFF
            b'<?xml': 'svg',  # SVG
            b'<svg': 'svg',  # SVG
        }

        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://google.com',
        }

        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValidationError("image_url")

        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url, timeout=10) as response:

                    if response.status != 200:
                        raise ValidationError("image_url")

                    content_type = response.headers.get('Content-Type', '').lower()

                    # If Content-Type suggests it's an image, accept it
                    if content_type.startswith('image/'):
                        return url

                    # If Content-Type is not an image, check the first few bytes of the content
                    content = await response.content.read(512)  # Read a small part of the content

                    # Compare the initial bytes to known image file signatures
                    for signature, img_type in IMAGE_SIGNATURES.items():

                        if content.startswith(signature):
                            if img_type == 'webp':

                                if b'WEBP' in content[8:16]:
                                    return url

                            else:
                                return url

                    raise ValidationError("image_url")

        except (aiohttp.ClientError, aiohttp.InvalidURL, asyncio.TimeoutError):
            raise ValidationError("image_url")

