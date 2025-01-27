import os

import asyncio
import discord
import mariadb as mariadb
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
import calendar

from .customlogging import log

async def setup(client):
    await client.add_cog(Updater(client))


class Updater(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()
        self.stopTimer = True

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def startautoroleupdate(self, ctx):
        self.stopTimer = False
        suppress = True
        await self.updateall(ctx, suppress)
        await self.autoroleupdate(ctx)
        await ctx.send(embed=discord.Embed(title="Auto role update started successfully!",
                                               description="All roles will be updated every 3 hours."))

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def stopautoroleupdate(self, ctx):
        self.stopTimer = True
        await ctx.send(embed=discord.Embed(title="Auto role update stop successfully!"))

    async def autoroleupdate(self, ctx):
        while True:
            await asyncio.sleep(3 * 60 * 60)
            if self.stopTimer is True:
                log("stopping auto updater")
                break
            else:
                log("starting autoupdater...")
            suppress = True
            await self.updateall(ctx, suppress)
            log("Updating all roles on timer...")

    @commands.command()
    async def checkautoroleupdate(self, ctx):
        if self.stopTimer is False:
            await ctx.send(embed=discord.Embed(title="Auto Role Update is currently ON", colour=0x6CC24A))
        elif self.stopTimer is True:
            await ctx.send(embed=discord.Embed(title="Auto Role Update is currently OFF", colour=0xF15025))


    @commands.hybrid_command(name='updateroles', description="Update your roles")
    async def updateroles(self, ctx):
        log(f"Updating roles for {ctx.author.nick}")
        roleupdate = await self.role_updater(ctx.author, ctx.guild)

        if roleupdate == 0:
            await ctx.send(embed=discord.Embed(title="You're not in our database!",
                description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca"),
                    ephemeral=True)
        else:
            await ctx.send(embed=discord.Embed(title="Your roles have been updated!",
                description=f"{ctx.author.mention}, chirp! Your roles are now up to date!"),
                    ephemeral=True)

        log(f"Completed updating all roles for {ctx.author.nick}\n", 'success')

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def refreshroles(self, ctx):
        """Admin Only: Refreshes roles for all users"""
        suppress = False
        await self.updateall(ctx, suppress)

    async def updateall(self, ctx, suppress):
        log("Updating all roles for all users")
        """Used to update roles for all users"""

        for member in ctx.guild.members:
            if not member.bot:
                log(f"Updating roles for {member.display_name}")
                await self.role_updater(member, ctx.guild)
                log(f"Completed updating all roles for {member.display_name}\n", 'success')
            else:
                pass
        if suppress is True:

            log("Completed updating all user roles\n    Suppressing discord notification \n", "success")
        else:
            await ctx.send(embed=discord.Embed(title="All roles have been updated",
                                               description="The roles of all users were updated successfully!"))
            log("Completed updating all user roles\n", "success")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log(f"{member} has joined the server")
        roleupdate = await self.role_updater(member, member.guild)
        log(f"Completed updating all roles for {member.display_name}\n", "success")

        dm = member.dm_channel
        if dm == None:
            dm = await member.create_dm()

        if roleupdate == 0:
            await dm.send(embed=discord.Embed(title="You're not in our database!",
                                              description="CHIRP!! {member.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca, then run ~updateroles in #introduce-yourself to be assigned your roles",
                                              colour=0xF23131))
        else:
            await dm.send(embed=discord.Embed(title="Welcome! Your roles have been assigned!",
                                              description=f"{member.mention}, chirp! Your roles have been added! Thanks for linking your discord!"))

    async def update_user_rating(self, guild, member: discord.Member, rating):

        s1Role = int(os.getenv('S1-ROLE'))
        s2Role = int(os.getenv('S2-ROLE'))
        s3Role = int(os.getenv('S3-ROLE'))
        c1Role = int(os.getenv('C1-ROLE'))
        c3Role = int(os.getenv('C3-ROLE'))
        i1Role = int(os.getenv('I1-ROLE'))
        i3Role = int(os.getenv('I3-ROLE'))

        S1 = guild.get_role(s1Role)
        S2 = guild.get_role(s2Role)
        S3 = guild.get_role(s3Role)
        C1 = guild.get_role(c1Role)
        C3 = guild.get_role(c3Role)
        I1 = guild.get_role(i1Role)
        I3 = guild.get_role(i3Role)

        # await member.remove_roles(S1, S2, S3, C1, C3, I1, I3)
        match rating:
            case 'S1':
                await member.add_roles(S1)
                log(f"Giving role S1 to {member.display_name}")
                await self.remove_excess_roles(member, [S2, S3, C1, C3, I1, I3])

            case 'S2':
                await member.add_roles(S2)
                log(f"Giving role S2 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S3, C1, C3, I1, I3])

            case 'S3':
                await member.add_roles(S3)
                log(f"Giving role S3 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, C1, C3, I1, I3])

            case 'C1':
                await member.add_roles(C1)
                log(f"Giving role C1 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C3, I1, I3])

            case 'C3':
                await member.add_roles(C3)
                log(f"Giving role C3 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C1, I1, I3])

            case 'I1':
                await member.add_roles(I1)
                log(f"Giving role I1 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C1, C3, I3])

            case 'I3':
                await member.add_roles(I3)
                log(f"Giving role I3 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C1, C3, I1])

    async def update_user_type(self, guild, member: discord.Member, status, instructor):
        # Takes in database info to add home, visiting, and instructor roles

        homeRole = int(os.getenv('HOME-ROLE'))
        visitorRole = int(os.getenv('VISITOR-ROLE'))
        guestRole = int(os.getenv('GUEST-ROLE'))
        mentorRole = int(os.getenv('MENTOR-ROLE'))
        instructorRole = int(os.getenv('INSTRUCTOR-ROLE'))

        Home = guild.get_role(homeRole)
        Visit = guild.get_role(visitorRole)
        Instructor = guild.get_role(instructorRole)
        Guest = guild.get_role(guestRole)
        Mentor = guild.get_role(mentorRole)

        # await member.remove_roles(Home, Visit, Instructor, Guest, Mentor)

        if status == None:
            await member.add_roles(Guest)
            log(f"Giving role {Guest.name} to {member.display_name}")
            await self.remove_excess_roles(member, [Home, Visit, Instructor, Mentor])
            return

        match status[0]:
            case 'home':
                await member.add_roles(Home)
                log(f"Giving role {Home.name} to {member.display_name}")
                if instructor == None:
                    await self.remove_excess_roles(member, [Visit, Instructor, Mentor, Guest])
                    return
                elif instructor[0] == 0:
                    await member.add_roles(Mentor)
                    log(f"Giving role {Mentor.name} to {member.display_name}")
                    await self.remove_excess_roles(member, [Visit, Instructor, Guest])

                elif instructor[0] == 1:
                    await member.add_roles(Instructor)
                    log(f"Giving role {Instructor.name} to {member.display_name}")
                    await self.remove_excess_roles(member, [Visit, Mentor, Guest])

            case 'visit':
                await member.add_roles(Visit)
                log(f"Giving role {Visit.name} to {member.display_name}")
                await self.remove_excess_roles(member, [Home, Instructor, Mentor, Guest])

            case 'instructor':
                await member.add_roles(Home)
                log(f"Giving role {Home.name} to {member.display_name}")
                await member.add_roles(Instructor)
                log(f"Giving role {Instructor.name} to {member.display_name}")
                await self.remove_excess_roles(member, [Visit, Guest, Mentor])

    async def top_controller(self, guild, member: discord.Member):
        TopRole = int(os.getenv('TOP-ROLE'))

        Top = guild.get_role(TopRole)

        mycurs = self.database_connect()
        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {member.id}")
        user = mycurs.fetchone()

        if not user:
            return

        # mycurs.execute(f"SELECT cid FROM roster ORDER BY currency DESC LIMIT 5")
        (_, daysInMonth) = calendar.monthrange(datetime.today().year, datetime.today().month)
        dateStart = datetime.today().replace(day=1, hour=0, minute=0, second=0).isoformat('T', 'seconds')
        dateEnd = datetime.today().replace(day=daysInMonth, hour=23, minute=59, second=59).isoformat('T', 'seconds')
        # print(f"start of month: {dateStart}, end of month: {dateEnd}")

        mycurs.execute(f"SELECT cid, SUM(duration) AS duration FROM {os.getenv('DB-NAME')}.session_logs WHERE session_start between '{dateStart}' and '{dateEnd}' GROUP BY cid  ORDER BY duration DESC LIMIT 5")
        topFive = []

        for i in mycurs:
            topFive.append(i[0])

        mycurs.close()

        if user[0] in topFive:
            log("Congrats for being in the top 5...")
            await member.add_roles(Top)
        else:
            if Top in member.roles:
                log("Not a top controller anymore...")
                await member.remove_roles(Top)

    async def set_nickname(self, guild, member: discord.Member, fname, lname, cid, cid_only, fullname):

        if member == guild.owner:
            return member

        if cid_only or len(f"{fname} - {cid}") > 32:
            updated_member = await member.edit(nick=str(cid))
        elif not fullname or len(f"{fname} {lname} - {cid}") > 32:
            updated_member = await member.edit(nick=f"{fname} - {cid}")
        else:
            updated_member = await member.edit(nick=f"{fname} {lname} - {cid}")

        log(f"Nickname set to {updated_member.nick}")
        return updated_member

    def database_connect(self):
        dbhost = os.getenv('DB-HOST')
        dbuser = os.getenv('DB-USER')
        dbpass = os.getenv('DB-PASS')
        dbname = os.getenv('DB-NAME')

        try:
            db = mariadb.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
        except mariadb.Error as e:
            log(f"Error connecting to MariaDB Platform: {e}", "error")
        else:
            log("Connected to the database", "success")
            mycurs = db.cursor()
            return mycurs

    async def remove_excess_roles(self, member, roles):
        for role in roles:
            if role in member.roles:
                await member.remove_roles(role)
                log(f"     Removing Role {role.name} to {member.display_name}")

    async def role_updater(self, member, guild):
        verifiedRole = int(os.getenv('VERIFIED-ROLE'))
        guestRole = int(os.getenv('GUEST-ROLE'))

        Verified = guild.get_role(verifiedRole)
        Guest = guild.get_role(guestRole)
        """Updates roles for a single user"""

        mycurs = self.database_connect()

        mycurs.execute(
            f"SELECT id, discord_user_id, rating_short, display_cid_only, display_last_name, display_fname, lname, permissions FROM users WHERE discord_user_id = {member.id}")
        user = mycurs.fetchone()
        # commented out for soft launch to allow time for users to link their accounts. When ready to remove roles from unlinked accounts uncomment the below statements.
        if not user:
            if Verified in member.roles:
                await member.edit(roles=[Verified, Guest])
                log("Not in the Database, but Verified", "warn")
            else:
                await member.edit(roles=[])
                log("Not in the Database!", "warn")

            return 0

        member = await self.set_nickname(guild, member, user[5], user[6], user[0], user[3], user[4])
        await member.add_roles(Verified)
        if user[7] > 0:
            await self.update_user_rating(guild, member, user[2])

        mycurs.execute(f"SELECT status FROM roster WHERE user_id = {user[0]}")
        status = mycurs.fetchone()
        mycurs.execute(f"SELECT is_instructor FROM teachers WHERE user_cid= {user[0]}")
        instructor = mycurs.fetchone()
        mycurs.close()

        await self.update_user_type(guild, member, status, instructor)
        await self.top_controller(guild, member)
