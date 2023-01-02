import os

import discord
import requests as requests
from discord.ext import commands
from discord.utils import get
from random import randint


class Misc(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def mochi(self, ctx):
        """Get chirped"""
        random = randint(1,14)
        image = discord.File(f"./mochi/{random}.jpg", filename=f"{random}.jpg")
        embed = discord.Embed()
        embed.set_image(url=f"attachment://{random}.jpg")
        await ctx.send(file=image, embed=embed)
    
    @commands.command()
    async def joinczvr(self, ctx):
        """Mochi will tell you how to be a CZVR controller"""
        embed = discord.Embed()
        embed.add_field(name="How To Join", value="\nTo join the CZVR FIR you will need to first be a member of VATCAN and have your S1 Rating. You can request a transfer by following the steps here: https://czvr.ca/join. \n\nOnce accepted you will receive a email from no-reply@vatcan.ca with further instructions before you are placed on the waitlist. \n\n*NOTE: I highly recomend whitelisting any @vatcan.ca or @czvr.ca Emails in your spam filter* \n\n**... I mean SQUAWK.**", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def link(self, ctx):
        """Mochi will tell you how to link your discord to our website"""
        embed = discord.Embed()
        embed.add_field(name="How To link Your Discord", value="\nTo link your Discord account and have your roles and name synced with the CZVR website goto https://czvr.ca and log in with your vatsim account, then goto your dashboard on the website and click 'link discord' then follow the steps.\n\nOnce youve done this it can take upto 24hrs for the bot to give you your roles, or you can update them manually with ~updateroles\n\n**... I mean SQUAWK.**", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def metar(self, ctx, icao):

        wxapikey = os.getenv('WX-API')
        # Make a request to the CheckWX API to get the airport information
        response = requests.get(f"https://api.checkwx.com/metar/{icao}/decoded?key={wxapikey}")
        data = response.json()

        # Check if the request was successful
        if response.status_code != 200:
            await ctx.send(
                "Error: Could not fetch airport information. Please check the ICAO code and try again.")
            return

        # Extract the relevant information from the response
        airport_name = data['data'][0]['icao']
        metar = data['data'][0]['raw_text']
        clouds = data['data'][0]['clouds']
        temperature = data['data'][0]['temperature']['celsius']
        dewpoint = data['data'][0]['dewpoint']['celsius']
        wind_speed = data['data'][0]['wind']['speed_kts']
        wind_direction = data['data'][0]['wind']['degrees']

        # Format the information into a message to send to the channel
        info_message = (
            f"Airport: {airport_name}\n"
            f"METAR: {metar}\n"
            f"Clouds: {clouds}\n"
            f"Temperature: {temperature}°C\n"
            f"Dewpoint: {dewpoint}°C\n"
            f"Wind Speed: {wind_speed} knots\n"
            f"Wind Direction: {wind_direction}°"
        )

        embed = discord.Embed(title=airport_name, description=metar)
        # embed.add_field(name="Clouds", value=clouds)
        embed.add_field(name="Temperature", value=f"{temperature}°C")
        embed.add_field(name="Dewpoint", value=f"{dewpoint}°C")
        embed.add_field(name="Wind", value=f"{wind_speed} knots @ {wind_direction}°")

        await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(Misc(client))
