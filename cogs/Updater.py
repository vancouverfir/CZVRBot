import os

import asyncio
import discord
import mariadb as mariadb
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
import calendar

async def setup(client):
    await client.add_cog(Updater(client))


class Updater(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def startautoroleupdate(self, ctx):
        global stopTimer
        stopTimer = False
        suppress = True
        await self.updateall(ctx, suppress)
        await self.autoroleupdate(ctx)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def stopautoroleupdate(self, ctx):
        global stopTimer
        stopTimer = True

    async def autoroleupdate(self, ctx):
        while True:
            await asyncio.sleep(3 * 60 * 60)
            if stopTimer is True:
                print("stopping auto updater")
                break
            else:
                print("starting autoupdater...")
            print("Updating all roles on timer...")
            suppress = True
            await self.updateall(ctx, suppress)

    @commands.command()
    async def updateroles(self, ctx):
        print(f"Updating roles for {ctx.author.nick}")
        roleupdate = await self.role_updater(ctx.author, ctx.guild)

        if roleupdate == 0:
            await ctx.send(embed=discord.Embed(title="You're not in our database!",
                                               description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca"))
        else:
            await ctx.send(embed=discord.Embed(title="Your roles have been updated!",
                                               description=f"{ctx.author.mention}, chirp! Your roles are now up to date!"))
        print(f"Completed updating all roles for {ctx.author.nick}\n")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def refreshroles(self, ctx):
        """Admin Only: Refreshes roles for all users"""
        suppress = False
        await self.updateall(ctx, suppress)

    async def updateall(self, ctx, suppress):
        print(f"({datetime.now()}) Updating all roles for all users")
        """Used to update roles for all users"""

        for member in ctx.guild.members:
            if not member.bot:
                print(f"({datetime.now()}) Updating roles for {member.display_name}")
                await self.role_updater(member, ctx.guild)
                print(f"({datetime.now()}) Completed updating all roles for {member.display_name}\n")
            else:
                pass
        if suppress is True:

            print(f"({datetime.now()}) Completed updating all user roles\n Suppressing discord notification \n")
        else:
            await ctx.send(embed=discord.Embed(title="All roles have been updated",
                                               description="The roles of all users were updated successfully!"))
            print(f"({datetime.now()}) Completed updating all user roles\n")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"{member} has joined the server")
        roleupdate = await self.role_updater(member, member.guild)
        print(f"Completed updating all roles for {member.display_name}\n")

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
                print(f"Giving Role S1 to {member.display_name}")
                await self.remove_excess_roles(member, [S2, S3, C1, C3, I1, I3])

            case 'S2':
                await member.add_roles(S2)
                print(f"Giving Role S2 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S3, C1, C3, I1, I3])

            case 'S3':
                await member.add_roles(S3)
                print(f"Giving Role S3 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, C1, C3, I1, I3])

            case 'C1':
                await member.add_roles(C1)
                print(f"Giving Role C1 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C3, I1, I3])

            case 'C3':
                await member.add_roles(C3)
                print(f"Giving Role C3 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C1, I1, I3])

            case 'I1':
                await member.add_roles(I1)
                print(f"Giving Role I1 to {member.display_name}")
                await self.remove_excess_roles(member, [S1, S2, S3, C1, C3, I3])

            case 'I3':
                await member.add_roles(I3)
                print(f"Giving Role I3 to {member.display_name}")
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
            print(f"Giving Role {Guest.name} to {member.display_name}")
            await self.remove_excess_roles(member, [Home, Visit, Instructor, Mentor])
            return

        match status[0]:
            case 'home':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.display_name}")
                if instructor == None:
                    await self.remove_excess_roles(member, [Visit, Instructor, Mentor, Guest])
                    return
                elif instructor[0] == 0:
                    await member.add_roles(Mentor)
                    print(f"Giving Role {Mentor.name} to {member.display_name}")
                    await self.remove_excess_roles(member, [Visit, Instructor, Guest])

                elif instructor[0] == 1:
                    await member.add_roles(Instructor)
                    print(f"Giving Role {Instructor.name} to {member.display_name}")
                    await self.remove_excess_roles(member, [Visit, Mentor, Guest])

            case 'visit':
                await member.add_roles(Visit)
                print(f"Giving Role {Visit.name} to {member.display_name}")
                await self.remove_excess_roles(member, [Home, Instructor, Mentor, Guest])

            case 'instructor':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.display_name}")
                await member.add_roles(Instructor)
                print(f"Giving Role {Instructor.name} to {member.display_name}")
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
        print(f"start of month: {dateStart}, end of month: {dateEnd}")

        mycurs.execute(f"SELECT cid, SUM(duration) AS duration FROM nyunhacvky.session_logs WHERE session_start between '{dateStart}' and '{dateEnd}' GROUP BY cid  ORDER BY duration DESC LIMIT 5")
        topFive = []

        for i in mycurs:
            topFive.append(i[0])

        mycurs.close()

        if user[0] in topFive:
            print("Congrats for being in the top 5...")
            await member.add_roles(Top)
        else:
            if Top in member.roles:
                print("Not a top controller Anymore...")
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

        print(f"nickname set to {updated_member.nick}")
        return updated_member

    def database_connect(self):
        dbhost = os.getenv('DB-HOST')
        dbuser = os.getenv('DB-USER')
        dbpass = os.getenv('DB-PASS')
        dbname = os.getenv('DB-NAME')

        try:
            db = mariadb.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
        else:
            print("Connected to the database")
            mycurs = db.cursor()
            return mycurs

    async def remove_excess_roles(self, member, roles):
        for role in roles:
            if role in member.roles:
                await member.remove_roles(role)
                print(f"Removing Role {role.name} to {member.display_name}")

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
                print("Not in the Database, but Verified")
            else:
                await member.edit(roles=[])
                print("Not in the Database!")

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
