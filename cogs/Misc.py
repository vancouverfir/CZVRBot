import os
from random import randint
from datetime import datetime

import discord
import requests as requests
from discord.ext import commands

from .CustomLogging import log


class Misc(commands.Cog):
    last_tz_error = datetime.now()

    def __init__(self, client):
        self.client = client

    @commands.hybrid_command(name='mochi', description="Get chirped")
    async def mochi(self, ctx):
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
        log("Timezone counter was reset!")

    @commands.hybrid_command(name='joinczvr', description="How to be a CZVR controller")
    async def joinczvr(self, ctx):
        embed = discord.Embed()
        embed.add_field(name="How To Join",
                        value="\nTo join the CZVR FIR you will need to first be a member of VATCAN and have your S1 Rating. You can request a transfer by following the steps here: https://czvr.ca/join. \n\nOnce accepted you will receive an email from no-reply@vatcan.ca with further instructions before you are placed on the waitlist. \n\n*NOTE: We highly recommend whitelisting any @vatcan.ca or @czvr.ca Emails in your spam filter* \n\n**... I mean SQUAWK.**",
                        inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='link', description="Mochi will tell you how to link your Discord to our Website")
    async def link(self, ctx):
        embed = discord.Embed()
        embed.add_field(name="How To link Your Discord",
                        value="\nTo link your Discord account head over to https://czvr.ca and log in. Once logged in go to your dashboard and click 'Link Discord' and follow the steps.\n\nIt may take up to 24hrs for the bot to give you your roles, or you can update them manually with ~updateroles\n\n**... I mean SQUAWK.**",
                        inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='metar', description="Get the METAR for an airport")
    async def metar(self, ctx, icao: str):
        icao = icao.upper()

        navcanada_url = f"https://plan.navcanada.ca/weather/api/alpha/?site={icao}&alpha=metar"
        navcanada_response = requests.get(navcanada_url)

        if navcanada_response.status_code == 200:
            navcanada_data = navcanada_response.json()

            if 'data' in navcanada_data and navcanada_data['data']:
                metar_text = navcanada_data['data'][0]['text']
                if "LWIS" in metar_text:
                    start_validity = navcanada_data['data'][0]['startValidity']
                    start_time = datetime.strptime(start_validity, "%Y-%m-%dT%H:%M:%S")
                    formatted_time = start_time.strftime("%H:%MZ")
                    embed = discord.Embed(title=f"LWIS for {icao}", description=f"```{metar_text}```", colour=0x6CC24A)
                    embed.add_field(name="Time", value=formatted_time, inline=False)
                    await ctx.send(embed=embed)
                    return
            else:
                log(f"Unable to fetch metar for {icao}", "warn")
                await ctx.send(embed=discord.Embed(
                    title="Unknown Airport",
                    description=f"Error: Could not fetch airport information. Please check the ICAO code and try again",
                    color=0xF23131
                ))
                return

        wxapikey = os.getenv('WX-API')
        checkwx_url = f"https://api.checkwx.com/metar/{icao}/decoded?key={wxapikey}"
        checkwx_response = requests.get(checkwx_url)

        if checkwx_response.status_code == 200:
            metar_data = checkwx_response.json()

            if 'data' in metar_data and metar_data['data']:
                airport_name = metar_data['data'][0]['station']['name']
                altimeter = metar_data['data'][0]['barometer']['hg']
                metar = metar_data['data'][0]['raw_text']
                temperature = metar_data['data'][0]['temperature']['celsius']
                dewpoint = metar_data['data'][0]['dewpoint']['celsius']
                visibility = metar_data['data'][0]['visibility']['miles']
                flight_condition = metar_data['data'][0]['flight_category']
                location = metar_data['data'][0]['station']['location']
                time = metar_data['data'][0]['observed'][-8:-3] + 'Z'

                try:
                    wind_speed = metar_data['data'][0]['wind']['speed_kts']
                    wind_direction = metar_data['data'][0]['wind']['degrees']
                except KeyError:
                    wind_speed = '0'
                    wind_direction = '000'

                match flight_condition:
                    case 'VFR':
                        colour = 0x6CC24A
                    case 'MVFR':
                        colour = 0xB2D33C
                    case 'IFR':
                        colour = 0xF15025
                    case 'LIFR':
                        colour = 0x873cab
                    case _:
                        colour = 0x000000

                embed = discord.Embed(title=airport_name, description=f"```{metar}```", colour=colour)
                embed.add_field(name="Flight Conditions", value=flight_condition)
                embed.add_field(name="Altimeter", value=altimeter)
                embed.add_field(name="Wind", value=f"{wind_direction} at {wind_speed} knots")
                embed.add_field(name="Time", value=time)
                embed.add_field(name="Temperature", value=f"{temperature}°C/{dewpoint}°C")
                embed.add_field(name="Visibility", value=f"{visibility} SM")
                embed.set_footer(text=location)

                await ctx.send(embed=embed)
            else:
                log(f"Unable to fetch metar for {icao}", "warn")
                await ctx.send(embed=discord.Embed(
                    title="Unknown Airport",
                    description=f"Error: Could not fetch airport information. Please check the ICAO code and try again",
                    color=0xF23131
                ))
                
                return
        else:
            log(f"Unable to fetch metar for {icao}", "warn")
            await ctx.send(embed=discord.Embed(
                title="Unknown Airport",
                description=f"Error: Could not fetch airport information. Please check the ICAO code and try again",
                color=0xF23131
            ))
        log(f"Metar for {icao} fetched successfully", "success")

    @commands.command(aliases=['whatcom'])
    async def huh(self, ctx):
        await ctx.send("<:huh:1040136701877698641>")

async def setup(client):
    await client.add_cog(Misc(client))
