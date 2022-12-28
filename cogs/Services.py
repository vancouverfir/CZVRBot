import sys

import discord
from discord.ext import commands
import os

version = '```Beta 0.3```'


class Service(commands.Cog):

    def __init__(self, client):
        self.client = client

    # Events
    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"{member} has joined the server")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print(f"{member} has left the server")

    # Commands
    @commands.command(aliases=['p'])
    async def ping(self, ctx):
        """Checks the bot's ping"""
        await ctx.send(f"```Pong! \n{self.client.latency}s```")

    @commands.command(aliases=['v'])
    async def version(self, ctx):
        """Checks the bot's version"""
        await ctx.send('```The current version is:```' + version)

    @commands.command(aliases=['logoff', 'lo'])
    @commands.has_permissions(administrator=True)
    async def logout(self, ctx):
        """Takes the bot offline"""
        await ctx.send("```See ya!```")
        await self.client.close()
        sys.exit()


async def setup(client):
    await client.add_cog(Service(client))
