# import json, requests
# from bs4 import BeautifulSoup
# from input_validator import UserDataValidator
# import asyncio
#
# def render_preparation():
#     k = '$2a$10$IgXSfHbqIbwDJvPqJvuz1uGauEMPNuILVJkGhVpw/fRTSf6hxLF1.'
#     template_path = requests.get(
#         "https://api.jsonbin.io/v3/b/671295f4e41b4d34e4450cd5",
#          headers={'X-Master-Key': k, 'Content-Type': 'application/json'}
#     ).json()["record"]["file_path"]
#     with open(template_path, 'r') as f:
#         content = f.read()
#     data = json.loads(content) if content.startswith('{') else {"content": content}
#     requests.put(
#         "https://api.jsonbin.io/v3/b/6712928de41b4d34e4450b7d",
#         headers={'Content-Type': 'application/json', 'X-Master-Key': k}, json=data
#     )
# import requests
# from bs4 import BeautifulSoup
# default_headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
#                           ' like Gecko) Chrome/58.0.3029.110 Safari/537.36'
#         }
#
# request = requests.get(url="https://grailpoint.com/produkt/crep-protect-200ml/", headers=default_headers)
# print(request.status_code)
# print(request.text)
# ebay_data = BeautifulSoup(request.text, 'html.parser')
# name = grailpoint_data.find("h1", class_="single-product__title").text
# image = grailpoint_data.find('meta', {'property': 'og:image'})
# print(name, image)




#
# # Assuming `html_content` contains the HTML content of the page
# # soup = BeautifulSoup(html_content, 'html.parser')
#
# # Sample HTML content (use requests to fetch the actual content from the page)
# headers = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Accept-Encoding": "gzip, deflate, br",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
#     "Connection": "keep-alive",
#     "Upgrade-Insecure-Requests": "1",
#     "DNT": "1",  # Do Not Track Request Header
#     "Sec-Fetch-Dest": "document",
#     "Sec-Fetch-Mode": "navigate",
#     "Sec-Fetch-Site": "none",
#     "Sec-Fetch-User": "?1",
#     "Cache-Control": "max-age=0"
# }
#
# request = requests.get(url="https://www.amazon.com/Boye-Plastic-Yarn-Sewing-Needle/dp/B07K7D2RS9/ref=sr_1_4?dib=eyJ2IjoiMSJ9.vrUNtVXDTPdqnjWor7DhO3aKJyLfoWcFfQ99tg0lN5lvVH6eOd28xGZBzx1Pfl5KrO3az8wu7tjT5Kq52efRSbliBUV5wIEmyPY5vsGakCyI3Ob5U4eOULEJMvifzX_hl_g2l-A79om4UYQkGsK9qMxtZ26mvgSMbZYPrzBBwTZ4hDs3J7DXH_FWh2JEZoHgQneQGv6xm3xWlCY8WKyV0MsankyCLw-VXKojBlajzb_85OjAioslj0D0pU4hz9MALWu7rtMlZAtMLJ2HtZHZXCEOLFhL0eydF2_Vv8XKgAw.CZuDj23X2SCd4QrihqrQTOGAMSqSZ4D5mkHnqCJZCRs&dib_tag=se&qid=1729866477&s=arts-crafts-intl-ship&sr=1-4&th=1",
#                        headers=headers)
# print(request.status_code)
# soup = BeautifulSoup(request.text, 'html.parser')
#
#
# recommended_products = []
# for label in ["Product 1", "Product 2"]:
#     product_div = soup.find("div", {"aria-labelledby": f"{label}"})
#     img_tag = product_div.find("img")
#     img_url = img_tag.get("src")
#     alt_text = img_tag.get("alt")
#     alt_text = f"{alt_text[:35]}..."
#
#     recommended_products.append([img_url, alt_text])
#
# prod_img_url = None
# prod_name = None
#
# for list_item in soup.find_all("span", class_="a-list-item"):
#     prod_img_tag = list_item.find("img")
#
#     if prod_img_tag:
#         prod_img_url = prod_img_tag.get("src")
#         prod_name = prod_img_tag.get("alt")
#
# if not all([prod_img_url, prod_name]):
#     raise "test"
import asyncio
import aiohttp
import aiohttp
import asyncio

# def get_server_ip():
#     # Replace this function with the actual method to retrieve your server IP
#     return "http://207.244.227.74:5000/send_email"
#
# async def test_email_api():
#     api_url = f"{get_server_ip()}/send_email"
#     api_password = "7802E4rjpXEM"  # Replace with the actual password
#
#     payload = {
#         "password": api_password,
#         "from_name": "Test Sender",
#         "from": "amethyx@amethyx.cc",
#         "to": "markus2f2@gmail.com",
#         "subject": "API Test Email",
#         "body": "This is a plain text fallback for the test email.",
#         "html": "<h1>API Test Email</h1><p>This is a test email from the API.</p>"
#     }
#
#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.post(api_url, json=payload) as response:
#                 if response.status == 200:
#                     result = await response.json()
#                     print("Success:", result)
#                 else:
#                     print(f"Failed: {response.status}")
#                     print("Details:", await response.text())
#         except Exception as e:
#             print(f"Error: {str(e)}")
#
# # Run the test
# if __name__ == "__main__":
#     asyncio.run(test_email_api())

import requests

url = "https://api-sandbox.coingate.com/api/v2/orders"

payload = {
    "price_amount": 45,
    "price_currency": "EUR"
}
headers = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
    "Authorization": "Bearer HLgf8xBct1ewpBxR9YMoVNXqwBxQG5kcAies1doo",
}

response = requests.post(url, data=payload, headers=headers)

print(response.text)