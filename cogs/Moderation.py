import discord
from discord.ext import commands
from .CustomLogging import log


class Moderation(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['c'])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amt=10):
        """Used to delete the last messages. (Default is 10 including the command)"""
        await ctx.channel.purge(limit=amt)
        log(f"Cleared {amt} messages\n")

    @commands.command(aliases=['k'])
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, mem: discord.Member, *, reason=None):
        """Used to kick members"""
        await mem.kick(reason=reason)
        await ctx.send( f'Kicked {mem.mention}')
        log(f"Kicked {mem.name}\n")

    @commands.command(aliases=['b'])
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, mem: discord.Member, *, reason=None):
        """Used to ban members"""
        await mem.ban(reason=reason)
        await ctx.send(f'Banned {mem.mention}')
        log(f"Banned {mem.name}\n")

    @commands.command(aliases=['ub'])
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, mem):
        """Used to unban members"""
        banned = [entry async for entry in ctx.guild.bans(limit=2000)]

        for ban_entry in banned:
            user = ban_entry.user

            if user.id == mem:
                await ctx.guild.unban(user)
                await ctx.send(f'Unbanned {user.mention}')
                log(f"Unbanned {user.name}\n")
                return

    @commands.command(pass_contest=True)
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, addremove, member: discord.Member, role: discord.Role):
        """Used to give roles to members"""

        if addremove == 'add':
            await member.add_roles(role)
            await ctx.send(f'{role} has been added to {member.nick}')

        elif addremove == 'remove':
            await member.remove_roles(role)
            await ctx.send(f'{role} have been removed to {member.nick}')

    @commands.command(pass_context=True)
    @commands.has_permissions(manage_channels=True)
    async def sendmessage(self, ctx, channel: discord.TextChannel, *, message):
        """Used to send a message in a specified channel"""

        if channel.permissions_for(ctx.guild.me).send_messages:
            await channel.send(message)
            log(f"Sent a message to {channel.name}: {message}\n")
        else:
            await ctx.send("I don't have permission to send messages in that channel.")

async def setup(client):
    await client.add_cog(Moderation(client))
