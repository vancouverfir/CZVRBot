import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import cogs.Updater as Updater

version = '```V1.1.1```'


class Service(commands.Cog):

    def __init__(self, client):
        self.client = client

    # Events
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print(f"{member} has left the server")

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


async def setup(client):
    await client.add_cog(Service(client))
