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
                        value="\nTo join the CZVR FIR you will need to first be a member of VATCAN. You can request a transfer by following the steps here: https://czvr.ca/join. \n\nOnce accepted you will receive an email from no-reply@vatcan.ca with further instructions before you are placed on the waitlist. \n\n*NOTE: We highly recommend whitelisting any @vatcan.ca or @czvr.ca Emails in your spam filter* \n\n**... I mean SQUAWK.**",
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
        try:
            navcanada_response = requests.get(navcanada_url, timeout=5)
            if navcanada_response.status_code == 200:
                navcanada_data = navcanada_response.json()
                if navcanada_data.get('data'):
                    metar_text = navcanada_data['data'][0]['text']
                    if "LWIS" in metar_text:
                        start_validity = navcanada_data['data'][0]['startValidity']
                        start_time = datetime.strptime(start_validity, "%Y-%m-%dT%H:%M:%S")
                        formatted_time = start_time.strftime("%H:%MZ")
                        embed = discord.Embed(title=f"LWIS for {icao}", description=f"```{metar_text}```", colour=0x6CC24A)
                        embed.add_field(name="Time", value=formatted_time, inline=False)
                        await ctx.send(embed=embed)
                        return
        except Exception as e:
            log(f"NavCanada check skipped: {e}", "info")

        wxapikey = os.getenv('WX-API')
        checkwx_url = f"https://api.checkwx.com/v2/metar/{icao}/decoded"
        headers = {'X-API-Key': wxapikey}
        checkwx_response = requests.get(checkwx_url, headers=headers)
        if checkwx_response.status_code == 200:
            metar_data = checkwx_response.json()
            if 'data' in metar_data and metar_data['data']:
                data = metar_data['data'][0]
                station = data.get('station')
                station = station if isinstance(station, dict) else {}
                airport_name = station.get('name', icao)
                raw_metar = data.get('raw_text', 'No METAR text')
                flight_condition = data.get('flight_category', 'N/A')
                color_map = {
                    'VFR': 0x6CC24A,
                    'MVFR': 0xB2D33C,
                    'IFR': 0xF15025,
                    'LIFR': 0x873cab
                }
                colour = color_map.get(flight_condition, 0x000000)
                embed = discord.Embed(title=airport_name, description=f"```{raw_metar}```", colour=colour)
                embed.add_field(name="Flight Conditions", value=flight_condition)

                pressure = data.get('pressure')
                pressure = pressure if isinstance(pressure, dict) else {}
                if pressure.get('hg'):
                    embed.add_field(name="Altimeter", value=pressure['hg'])

                wind = data.get('wind')
                wind = wind if isinstance(wind, dict) else {}
                if wind:
                    speed = wind.get('speed')
                    speed = speed if isinstance(speed, dict) else {}
                    w_speed = speed.get('kts', '0')
                    w_dir = wind.get('degrees', '000')
                    gust = wind.get('gust')
                    gust = gust if isinstance(gust, dict) else {}
                    gust_kts = gust.get('kts')
                    wind_str = f"{w_dir}° at {w_speed} kts"
                    if gust_kts:
                        wind_str += f" (gusting {gust_kts} kts)"
                    embed.add_field(name="Wind", value=wind_str)
                observed = data.get('observed')
                if observed and isinstance(observed, str):
                    embed.add_field(name="Time", value=f"{observed[11:16]}Z")
                temperature = data.get('temperature')
                temperature = temperature if isinstance(temperature, dict) else {}
                dewpoint = data.get('dewpoint')
                dewpoint = dewpoint if isinstance(dewpoint, dict) else {}
                temp = temperature.get('celsius')
                dew = dewpoint.get('celsius')
                if temp is not None:
                    embed.add_field(name="Temperature", value=f"{temp}°C/{dew if dew is not None else '??'}°C")
                visibility = data.get('visibility')
                visibility = visibility if isinstance(visibility, dict) else {}
                vis = visibility.get('miles')
                if vis:
                    embed.add_field(name="Visibility", value=f"{vis} SM")
                location = station.get('location')
                if location:
                    embed.set_footer(text=location)
                await ctx.send(embed=embed)
                log(f"Metar for {icao} fetched successfully", "success")
                return
        log(f"Unable to fetch metar for {icao}", "warn")
        await ctx.send(embed=discord.Embed(
            title="Unknown Airport",
            description=f"Error: Could not fetch airport information. Please check the code and try again.",
            color=0xF23131
        ))

    @commands.command(aliases=['whatcom'])
    async def huh(self, ctx):
        await ctx.send("<:huh:1040136701877698641>")

async def setup(client):
    await client.add_cog(Misc(client))
