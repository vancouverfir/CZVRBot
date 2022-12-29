import discord
from discord.ext import commands
from discord.utils import get
from random import randint


class Misc(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def mochi(self, ctx):
        random = randint(1,7)
        image = discord.File(f"./mochi/{random}.jpg", filename=f"{random}.jpg")
        embed = discord.Embed()
        embed.set_image(url=f"attachment://{random}.jpg")
        await ctx.send(file=image, embed=embed)


async def setup(client):
    await client.add_cog(Misc(client))
