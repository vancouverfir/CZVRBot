import os
from datetime import time, timezone

import discord
from discord.ext import commands, tasks

from channel_displays import (
    home_controller_count,
    utc_channel_name,
    vancouver_channel_name,
)
from .CustomLogging import log


FIVE_MINUTE_BOUNDARIES = [
    time(hour=hour, minute=minute, tzinfo=timezone.utc)
    for hour in range(24)
    for minute in range(0, 60, 5)
]


class ChannelDisplays(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.utc_channel_id = int(os.getenv("UTC-CLOCK-CHANNEL", "1369519082973691904"))
        self.vancouver_channel_id = int(os.getenv("VANCOUVER-CLOCK-CHANNEL", "1369519620419227698"))
        self.home_controllers_channel_id = int(os.getenv("HOME-CONTROLLERS-CHANNEL", "1369518429274505227"))
        self.guild_id = int(os.getenv("GUILD-ID", "0"))
        self.home_role_id = int(os.getenv("HOME-ROLE", "720782657516077126"))

    async def cog_load(self):
        self.clock_update.start()
        self.home_controllers_update.start()

    def cog_unload(self):
        self.clock_update.cancel()
        self.home_controllers_update.cancel()

    async def update_channel_name(self, channel_id: int, desired_name: str):
        channel = self.client.get_channel(channel_id)
        if channel is None:
            log(f"Could not find display channel {channel_id}", "error")
            return

        if channel.name == desired_name:
            return

        try:
            await channel.edit(name=desired_name, reason="Update live server display")
        except discord.Forbidden:
            log(f"Missing permission to rename display channel {channel_id}", "error")
        except discord.HTTPException as error:
            log(f"Could not rename display channel {channel_id}: {error}", "error")

    @tasks.loop(time=FIVE_MINUTE_BOUNDARIES)
    async def clock_update(self):
        await self.update_channel_name(self.utc_channel_id, utc_channel_name())
        await self.update_channel_name(self.vancouver_channel_id, vancouver_channel_name())

    @clock_update.before_loop
    async def before_clock_update(self):
        await self.client.wait_until_ready()

    @tasks.loop(hours=1)
    async def home_controllers_update(self):
        guild = self.client.get_guild(self.guild_id)
        if guild is None:
            log(f"Could not find guild {self.guild_id} for home controller count", "error")
            return

        count = home_controller_count(guild.members, self.home_role_id)
        await self.update_channel_name(
            self.home_controllers_channel_id,
            f"Home Controllers: {count}",
        )

    @home_controllers_update.before_loop
    async def before_home_controllers_update(self):
        await self.client.wait_until_ready()


async def setup(client):
    await client.add_cog(ChannelDisplays(client))
