import sys

import random
import asyncio
import datetime
import discord
from datetime import timedelta
from discord.ext import commands
from .CustomLogging import log
from discord.ui import View, Button

version = '```1```'

CHANNEL_ID = 1322096208751099964
ROLE_ID = 1173032507818651699

YES = ["Absolutely!", "Count me in", "Totally", "Fo shizzle"]
MAYBE = ["Maybe if Mom lets me", "Possibly", "We'll see", "Can't contrizzle"]
NO = ["Nope", "Not happening", "Definitely not", "Might drop bizzle"]

class Service(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.wcw_task = None

    async def cog_load(self):
        """Start the scheduled WCW poll when the cog loads"""
        self.wcw_task = asyncio.create_task(self.schedule_wcw_poll())

    def cog_unload(self):
        """Cancel scheduled task if cog is unloaded"""
        if self.wcw_task:
            self.wcw_task.cancel()

    # Commands
    @commands.command(aliases=['p'])
    async def ping(self, ctx):
        """Checks the bot's ping"""
        await ctx.send(embed=discord.Embed(title="Pong!",description=f"```{self.client.latency} seconds```"))

    @commands.command(aliases=['v'])
    async def version(self, ctx):
        """Checks the bot's version"""
        await ctx.send(embed=discord.Embed(title="Version",description=f"The current version is {version}"))

    @commands.command(aliases=['logoff', 'lo'])
    @commands.has_permissions(administrator=True)
    async def logout(self, ctx):
        """Takes the bot offline"""
        await ctx.send(embed=discord.Embed(title="See Ya!",description="It's my time to go! I'm outta here!"))
        await self.client.close()
        sys.exit()

    async def schedule_wcw_poll(self):
        """Send the poll every Sunday at 08:00 UTC (12 hours before Event)"""
        await self.client.wait_until_ready()
        while not self.client.is_closed():
            now = datetime.datetime.utcnow()
            days_ahead = 6 - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            next_sunday = (now + datetime.timedelta(days=days_ahead)).replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            if next_sunday <= now:
                next_sunday += datetime.timedelta(weeks=1)

            wait_seconds = (next_sunday - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            await self.send_wcw_prompt()

    async def send_wcw_prompt(self):
        channel = self.client.get_channel(CHANNEL_ID)
        if not channel:
            print("ERROR: WCW channel not found!")
            return

        role_ping = f"<@&{ROLE_ID}>"

        embed = discord.Embed(
            title="Weekly WCW Poll",
            description="Do you want me to post the WCW poll?",
            color=discord.Color.blurple()
        )

        view = WCWPromptView()
        await channel.send(content=role_ping, embed=embed, view=view)


class WCWPromptView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def remove_buttons(self, interaction: discord.Interaction):
        """Remove all buttons after a click"""
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: Button):
        await self.remove_buttons(interaction)

        try:
            await interaction.response.send_message("✅ Created!", ephemeral=False)

            channel = interaction.client.get_channel(CHANNEL_ID)

            options = [
                random.choice(YES),
                random.choice(MAYBE),
                random.choice(NO)
            ]

            poll = discord.Poll(
                question="🐦 Will you be controlling this Weekend for WCW?",
                duration=timedelta(hours=11),
                multiple=False
            )

            for option in options:
                poll.add_answer(text=option)

            await channel.send(poll=poll)

        except Exception as e:
            print("❌ ERROR Creating WCW poll! ", e)
            await interaction.followup.send("❌ Failed to create WCW poll!", ephemeral=False)

    @discord.ui.button(label="I will post it instead", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: Button):
        await self.remove_buttons(interaction)
        await interaction.response.send_message("✅ Got it, you’ll post instead!", ephemeral=False)


async def setup(client):
    await client.add_cog(Service(client))
