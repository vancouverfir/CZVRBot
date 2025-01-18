import os
from random import randint
from datetime import datetime

import discord
import requests as requests
from discord.ext import commands

from .customlogging import log


class Misc(commands.Cog):
    last_tz_error = datetime.now()

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def mochi(self, ctx):
        """Get chirped"""
        random = randint(1, 15)
        image = discord.File(f"./mochi/{random}.jpg", filename=f"{random}.jpg")
        embed = discord.Embed()
        embed.set_image(url=f"attachment://{random}.jpg")
        await ctx.send(file=image, embed=embed)

    @commands.command()
    async def tz(self, ctx):
        """Show the number of days since the last time zone mistake"""
        embed = discord.Embed()
        days = (datetime.now() - Misc.last_tz_error).days
        hours = (datetime.now() - Misc.last_tz_error).seconds // 3600
        minutes = ((datetime.now() - Misc.last_tz_error).seconds // 60) % 60
        text = str(days) + " days, " + str(hours).zfill(2) + "h" + str(minutes).zfill(2) + "m"
        embed.add_field(name="Since Timezone Issue",
                        value=text,
                        inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def resettz(self, ctx):
        """Reset the timezone mistake counter"""
        Misc.last_tz_error = datetime.now()
        await ctx.message.add_reaction("<:huh:1040136701877698641>")
        log("Timezone counter was reset :(")

    @commands.command()
    async def joinczvr(self, ctx):
        """Mochi will tell you how to be a CZVR controller"""
        embed = discord.Embed()
        embed.add_field(name="How To Join",
                        value="\nTo join the CZVR FIR you will need to first be a member of VATCAN and have your S1 Rating. You can request a transfer by following the steps here: https://czvr.ca/join. \n\nOnce accepted you will receive a email from no-reply@vatcan.ca with further instructions before you are placed on the waitlist. \n\n*NOTE: I highly recommend whitelisting any @vatcan.ca or @czvr.ca Emails in your spam filter* \n\n**... I mean SQUAWK.**",
                        inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def link(self, ctx):
        """Mochi will tell you how to link your discord to our website"""
        embed = discord.Embed()
        embed.add_field(name="How To link Your Discord",
                        value="\nTo link your Discord account and have your roles and name synced with the CZVR website goto https://czvr.ca and log in with your vatsim account, then goto your dashboard on the website and click 'link discord' then follow the steps.\n\nOnce you've done this it can take upto 24hrs for the bot to give you your roles, or you can update them manually with ~updateroles\n\n**... I mean SQUAWK.**",
                        inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def metar(self, ctx, icao):

        wxapikey = os.getenv('WX-API')
        # Make a request to the CheckWX API to get the airport information
        response = requests.get(f"https://api.checkwx.com/metar/{icao}/decoded?key={wxapikey}")
        data = response.json()

        # Check if the request was successful
        if response.status_code != 200:
            await ctx.send(embed=discord.Embed(title="Service Unavailable",
                                               description="Error: Could not connect to our metar service. Try again later.",
                                               color=0xF23131))
            log("Unable to connect to metar service", "error")
            return

        if data['results'] == 0:
            await ctx.send(embed=discord.Embed(title="Unknown Airport",
                                               description="Error: Could not fetch airport information. Please check the ICAO code and try again.",
                                               color=0xF23131))
            
            log(f"Unable to fetch metar for {icao}", "warn")
            return

        # Extract the relevant information from the response
        airport_name = data['data'][0]['station']['name']
        altimeter = data['data'][0]['barometer']['hg']
        metar = data['data'][0]['raw_text']
        clouds = data['data'][0]['clouds']
        temperature = data['data'][0]['temperature']['celsius']
        dewpoint = data['data'][0]['dewpoint']['celsius']
        try:
            wind_speed = data['data'][0]['wind']['speed_kts']
            wind_direction = data['data'][0]['wind']['degrees']
        except:
            wind_speed = '0'
            wind_direction = '000'
        visibility = data['data'][0]['visibility']['miles']
        flight_condition = data['data'][0]['flight_category']
        location = data['data'][0]['station']['location']
        time = data['data'][0]['observed'][-8:-3] + 'Z'

        match flight_condition:
            case 'VFR':
                colour = 0x6CC24A
            case 'MVFR':
                colour = 0xB2D33C
            case 'IFR':
                colour = 0xE3B031
            case 'LIFR':
                colour = 0xF15025
            case _:
                colour = 0x000000

        embed = discord.Embed(title=airport_name, description=f"```{metar}```", colour=colour)
        # embed.add_field(name="Clouds", value=clouds)
        embed.add_field(name="Flight Conditions", value=flight_condition)
        embed.add_field(name="Altimeter", value=altimeter)
        embed.add_field(name="Wind", value=f"{wind_speed} knots @ {wind_direction}°")
        embed.add_field(name="Time", value=time)
        embed.add_field(name="Temperature", value=f"{temperature}°C/{dewpoint}°C")
        embed.add_field(name="Visibility", value=f"{visibility} SM")
        embed.set_footer(text=location)

        await ctx.send(embed=embed)

        log(f"Metar for {icao} fetched successfully", "success")


    @commands.command(aliases=['whatcom'])
    async def huh(self, ctx):
        await ctx.send("<:huh:1040136701877698641>")


async def setup(client):
    await client.add_cog(Misc(client))
