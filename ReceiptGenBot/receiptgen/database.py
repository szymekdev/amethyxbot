import aiohttp
import asyncio
import datetime


class ScrapedWebLink:
    base_url = "http://localhost:8000/api/"

    def __init__(self, url):
        self.url = url

    async def save_scraped_content(self, title, content):
        data = {
            "url": self.url,
            "title": title,
            "content": content,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ScrapedWebLink.base_url}save-scrape-content/", json=data) as response:
                response = await response.json()

                return response.get("success", False)

    async def get_scraped_content(self):
        data = {
            "url": self.url
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ScrapedWebLink.base_url}get-scraped-content/", json=data) as response:
                response = await response.json()

                return response.get("content", None)



class GuildAPI:
    BASE_URL = "http://localhost:8000/api"

    def __init__(self, guild_id=None):
        self.guild_id = guild_id

    @staticmethod
    def _handle_response(response):
        """
        Handle the API response and raise an exception if needed.
        :param response: Response object from requests library.
        :return: Parsed JSON response.
        """
        return response

    async def create_guild(self, owner_id, name, guild_id, members=None):

        data = {
            "owner_id": owner_id,
            "name": name,
            "guild_id": guild_id,
            "members": members
        }

        url = f"{self.BASE_URL}/guild/"

        data = {key: value for key, value in data.items() if value is not None}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                response = await response.json()

        return self._handle_response(response)

    async def get_guild(self):
        if self.guild_id is None:
            raise "include a guild_id when init"

        url = f"{self.BASE_URL}/guild/{self.guild_id}/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response = await response.json()

        return self._handle_response(response)

    async def updater_guild(self, purchase_channel=None, notification_channel=None, access_role=None):

        data = {
            "notification_channel": notification_channel,
            "purchase_channel": purchase_channel,
            "access_role": access_role
        }

        url = f"{self.BASE_URL}/guild/{self.guild_id}/"

        data = {key: value for key, value in data.items() if value is not None}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=data) as response:
                response = await response.json()

        return self._handle_response(response)

    async def members_without_access(self):

        url = f"{self.BASE_URL}/users-without-access/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response = await response.json()

        return self._handle_response(response)


class GuildMemberAPI:
    BASE_URL = "http://localhost:8000/api"

    def __init__(self, guild_id=None, member_id=None):
        """
        Initialize the API client.
        :param guild_id: Optional guild ID for specific operations.
        :param member_id: Optional member ID for specific operations.
        """
        self.guild_id = guild_id
        self.member_id = member_id
        self.url = self._construct_url()

    def _construct_url(self):
        """
        Construct the URL based on initialized guild_id and member_id.
        :return: URL string for API interactions.
        """
        if self.guild_id and self.member_id:
            return f"{self.BASE_URL}/guild/{self.guild_id}/member/{self.member_id}/"
        else:
            return f"{self.BASE_URL}/guild-member/"

    @staticmethod
    def _handle_response(response):
        """
        Handle the API response and raise an exception if needed.
        :param response: Response object from requests library.
        :return: Parsed JSON response.
        """
        return response

    async def get_guild_member(self):
        """Retrieve the details of a specific guild member."""

        url = f"{self.BASE_URL}/guild/{self.guild_id}/member/{self.member_id}/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response = await response.json()

        return self._handle_response(response)

    async def create_guild_member(self, guild_id, member_id, email=None, refresh_token=None,
                                  sent_ended_notif=False, notification_channel=None, hours=None, days=None):
        """Create a new guild member."""
        url = f"{self.BASE_URL}/guild-member/"
        data = {
            "guild": guild_id,
            "member": member_id,
            "email": email,
            "hours": hours,
            "days": days,
            "refresh_token": refresh_token,
            "sent_ended_notif": sent_ended_notif,
            "notification_channel": notification_channel
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                response = await response.json()

        return self._handle_response(response)

    async def update_guild_member(self, email=None, refresh_token=None,
                                  sent_ended_notif=None, notification_channel=None, days=None,
                                  hours=None, remove_access=None):
        """Update the guild member's details."""

        url = f"{self.BASE_URL}/guild/{self.guild_id}/member/{self.member_id}/"
        data = {
            "email": email,
            "hours": hours,
            "remove_access": remove_access,
            "days": days,
            "refresh_token": refresh_token,
            "sent_ended_notif": sent_ended_notif,
            "notification_channel": notification_channel
        }
        # Remove None values from data to avoid sending them in the request
        data = {key: value for key, value in data.items() if value is not None}

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=data) as response:
                response = await response.json()

        return self._handle_response(response)

    async def delete_guild_member(self):
        """Delete the guild member."""
        url = f"{self.BASE_URL}/guild/{self.guild_id}/member/{self.member_id}/"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url) as response:
                response = await response.json()

        if response.status_code == 204:
            return {"status": "Deleted"}
        else:
            return self._handle_response(response)


class UserData:
    base_url = "http://localhost:8000/api/discord-user/"

    def __init__(self, discord_user_id):
        self.discord_user_id = int(discord_user_id)

    async def set_email(self, email):
        data = {
            "email": email
        }
        result = await self._update_discord_user(data)

        return result.get("success", False)

    async def give_access(self, days: int):

        data = {
            "additional_days": days
        }

        result = await self._update_discord_user(data)
        return result.get("success", False)

    async def get_email(self):
        result = await self._fetch_discord_user(self.discord_user_id)

        if not result.get("success"):
            return None

        return result["user"].get("email", None)

    async def get_access(self):

        """returns remaining access time and if user has access"""

        result = await self._fetch_discord_user(self.discord_user_id)

        if not result.get("success"):
            return False, None

        access_end = result["user"].get("access_end", False)
        has_access = result["user"].get("has_access")

        if access_end:
            try:
                access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S.%f%z")
            except ValueError:
                try:
                    access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S%z")
                except ValueError:

                    access_end = datetime.datetime.strptime(access_end, "%Y-%m-%dT%H:%M:%S")

        return has_access, access_end

    @staticmethod
    async def _fetch_discord_user(discord_user_id):
        url = f'{UserData.base_url}{discord_user_id}/'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    @staticmethod
    async def create_discord_user(discord_user_id, email=None) -> bool:
        data = {
            "discord_user_id": str(discord_user_id),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(UserData.base_url, json=data) as response:
                result = await response.json()
                return result.get("success", False)

    async def _update_discord_user(self, update_data):
        url = f"{UserData.base_url}{self.discord_user_id}/update/"

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=update_data) as response:
                return await response.json()

    @staticmethod
    async def is_user(discord_user_id) -> bool:
        result = await UserData._fetch_discord_user(str(discord_user_id))
        return result.get("success", False)

    @staticmethod
    async def get_expired_access_users() -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/expired-access-users/") as response:

                data = await response.json()

            if data.get("success"):
                return data["users"]

            else:
                raise "error fetching users"


class Ticket:
    base_url = "http://localhost:8000/api/ticket/"

    @staticmethod
    async def create_ticket(channel_id, user_id):
        data = {
            "channel_id": str(channel_id),
            "user_id": str(user_id)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{Ticket.base_url}create/", json=data) as response:
                result = await response.json()

                if not result.get("success"):
                    return None

                return result["ticket"].get("ticket_id", None)

    @staticmethod
    async def delete_ticket(channel_id):
        data = {
            "channel_id": str(channel_id)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{Ticket.base_url}delete/", json=data) as response:
                result = await response.json()
                return result.get("success", False)

    @staticmethod
    async def get_non_deleted():
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{Ticket.base_url}not-deleted/") as response:
                result = await response.json()

                return result.get("channels", False)


if __name__ == '__main__':
    # gm = GuildMemberAPI(guild_id=1255986026669674616, member_id=712728123040596008)
    # print(gm.update_guild_member(remove_access=True))
    async def main():
        db = GuildMemberAPI(guild_id="1269322998909898852", member_id="712728123040596008")
        print(await db.get_guild_member())

    asyncio.run(main())