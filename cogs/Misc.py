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
    
    @commands.command()
    async def joinczvr(self, ctx):
        embed = discord.Embed()
        embed.add_field(name="How To Join", value="To join the CZVR FIR you will need to first be a member of VATCAN and have your S1 Rating. You can request a transfer by following the steps here: https://czvr.ca/join. Once accepted you will receive a email from no-reply@vatcan.ca with further instructions before you are placed on the waitlist. \n\n*NOTE: I highly recomend whitelisting any @vatcan.ca or @czvr.ca Emails in your spam filter* \n\n**... I mean SQUAWK.**", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def link(self, ctx):
        await ctx.send("```To link your Discord account and have your roles and name synced with the CZVR website goto https://czvr.ca and log in with your vatsim account, then goto your dashboard on the website and click 'link discord' then follow the steps.\nOnce youve done this it can take upto 24hrs for the bot to give you your roles, or you can update them manually with ~updateroles\n\n**... I mean SQUAWK.**```")

async def setup(client):
    await client.add_cog(Misc(client))
