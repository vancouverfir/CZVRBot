import os
import discord
import dotenv
import asyncio

from discord.ext import commands
from cogs.customlogging import log

dotenv.load_dotenv()

token = os.getenv('BOT-TOKEN')

intents = discord.Intents.all()
# intents.message_content = True

client = commands.Bot(command_prefix='~', intents=intents, case_insensitive=True)


@client.event
async def on_ready():
    log(f"We have logged in as {client.user}", "success")

    await client.tree.sync()
    log(f'Slash commands synced', "success")

    activity = discord.Activity(type=discord.ActivityType.watching, name="the Events Team for Time Zone errors")
    await client.change_presence(status=discord.Status.online, activity=activity)

# Cog Loading
@client.command()
@commands.has_permissions(administrator=True)
async def load(ctx, extension):
    """Used to load cogs"""
    await client.load_extension(f'cogs.{extension}')


@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension):
    """Used to unload cogs"""
    await client.unload_extension(f'cogs.{extension}')


async def loadallcogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and filename != "customlogging.py":
            # try:
            await client.load_extension(f'cogs.{filename[:-3]}')
            log(f"Loaded cog {filename[:-3]}", "success")
            # except:
            #     log(f"Failed to load cogs.{filename[:-3]}", "error")



# Errors
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Missing Requirements", description='```Beep, You forgot to include a required argument```', colour = 0xF23131))

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(title="Missing Permissions", description='```CHIRP!! You do not have the permissions required to use this command```', colour = 0xF23131))
        log(f"User {ctx.author.nick} does not have permissions to run {ctx.message.content}", "warn")

    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(title="Unknown Command", description='```Sad Mochi noises```', colour = 0xF23131))
        log(f'Unkown command: {error.args[0]}', 'error')

    else:
        await ctx.send(embed=discord.Embed(title="An Error Has Occured", description=error, colour = 0xF23131))
        log(error, 'error')        

async def main():
    await loadallcogs()
    await client.start(token)


asyncio.run(main())
