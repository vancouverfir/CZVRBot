import os
from random import randint

import discord
import requests as requests
from discord.ext import commands


class ATC(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def makebooking(self, ctx, cs, startdate, starttime, enddate, endtime):
        Valid_Aiports = ["CYVR", "CYYJ", "CYLW", "CYCD", "CYQQ", "CYXX", "CZBB", "CYXS"]
        Valid_Positions = ["_DEL", "_GND", "_TWR", "_DEP", "_APP", "_CTR", "_FSS"]

        if cs[:4] not in Valid_Aiports or cs[4:] not in Valid_Positions:
            await ctx.send(f"{cs} is not a valid position")
            return

        cid = ctx.author.nick.split()[-1]
        print(cid)

async def setup(client):
    await client.add_cog(ATC(client))
