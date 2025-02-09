import os

import asyncio
import mariadb as mariadb
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, time, timezone
import calendar


from .CustomLogging import log

async def setup(client):
    await client.add_cog(Updater(client))

times = [time(hour=3), time(hour=6), time(hour=9), time(hour=12), time(hour=15), time(hour=18), time(hour=21), time(hour=0)]


class Updater(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()


    @commands.hybrid_command(name='updateroles', description="Update your roles")
    async def updateroles(self, ctx):
        log(f"Updating roles for {ctx.author.nick}")
        db = self.database_connect()
        if not db:
            log("Failed to connect to database", "error")
            return

        mycurs = db.cursor()

        roleupdate = await self.role_updater(ctx.author, ctx.guild, mycurs)

        if roleupdate == 0:
            await ctx.send(embed=discord.Embed(title="You're not in our database!",
                description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca"),
                    ephemeral=True)
        else:
            await ctx.send(embed=discord.Embed(title="Your roles have been updated!",
                description=f"{ctx.author.mention}, chirp! Your roles are now up to date!"),
                    ephemeral=True)

        log(f"Completed updating all roles for {ctx.author.nick}\n", 'success')

    @commands.hybrid_command(alias='1')
    @commands.has_permissions(manage_roles=True)
    async def refreshroles(self, ctx):
        """Admin Only: Refreshes roles for all users"""

        await ctx.send(embed=discord.Embed(title="Started"), ephemeral=True)
        await self.updateall(False)

    @tasks.loop(time=times)
    async def updateall(self, suppress=True):
        """Used to update roles for all users with a single DB connection"""
        try:
            log("Batch updating roles for all users")

            guild = self.client.get_guild(int(os.getenv('GUILD-ID')))
            dev_channel = self.client.get_channel(int(os.getenv('DEV-CHANNEL')))

            # Establish a single DB connection
            db = self.database_connect()
            if not db:
                log("Failed to connect to database", "error")
                return

            mycurs = db.cursor()

            for member in guild.members:
                if not member.bot:
                    log(f"Updating roles for {member.display_name}")
                    await self.role_updater(member, guild, mycurs)
                    log(f"Completed updating roles for {member.display_name}\n", "success")

            # Close the DB connection after all users are processed
            mycurs.close()
            db.close()

            if suppress:
                log("Completed updating all user roles\n    Suppressing discord notification \n", "success")
            else:
                await dev_channel.send(embed=discord.Embed(
                    title="All roles have been updated",
                    description="The roles of all users were updated successfully!"
                ))
                log("Completed updating all user roles\n", "success")

        except Exception as e:
            log(f"updateall loop encountered an error: {e}", "error")

    @commands.Cog.listener()
    async def on_ready(self):
        self.updateall.start()

    @updateall.after_loop
    async def autoroleupdatecancel(self):
            if self.updateall.is_being_cancelled():
                dev_channel = self.client.get_channel(int(os.getenv('DEV-CHANNEL')))
                await dev_channel.message.send(embed=discord.Embed(title="Auto Role Updater has been cancelled"))
                log("Auto Role Updater was cancelled", "error")

    @commands.command()
    async def nextupdate(self, ctx):
        next = self.updateall.next_iteration
        now = datetime.now(timezone.utc)
        diff = next - now
        hours = diff.seconds // 3600
        mins = (diff.seconds // 60)  % 60

        await ctx.send(embed=discord.Embed(title=f"Auto Role Updater is scheduled to run next at {self.updateall.next_iteration.strftime('%H:%M')}Z", description=f"That's in {hours} hours and {mins} minutes"))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log(f"{member} has joined the server")
        roleupdate = await self.role_updater(member, member.guild)
        log(f"Completed updating all roles for {member.display_name}\n", "success")

        dm = member.dm_channel
        if dm == None:
            dm = await member.create_dm()

        if roleupdate == 0:
            await dm.send(embed=discord.Embed(title="You're not in our database!", description="CHIRP!! {member.mention}, you are not in our database, please link your discord account in your dashboard at https://www.czvr.ca, then run /updateroles to be assigned your roles", colour=0xF23131))
        else:
            await dm.send(embed=discord.Embed(title="Welcome! Your roles have been assigned!", description=f"{member.mention}, chirp! Your roles have been added! Thanks for linking your discord!"))


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log(f"{member.nick} has left the server")
        log_channel = self.client.get_channel(int(os.getenv('LOG-CHANNEL')))

        await log_channel.send(embed=discord.Embed(title=f"{member.nick} has left the server"))

    async def update_user_rating(self, guild, member: discord.Member, rating, add, remove, roles):

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
                if S1 not in roles:
                    add.append(S1)
                    log(f"Giving role S1 to {member.display_name}")
                    remove.extend([S2, S3, C1, C3, I1, I3])

            case 'S2':
                if S2 not in roles:
                    add.append(S2)
                    log(f"Giving role S2 to {member.display_name}")
                    remove.extend([S1, S3, C1, C3, I1, I3])

            case 'S3':
                if S3 not in roles:
                    add.append(S3)
                    log(f"Giving role S3 to {member.display_name}")
                    remove.extend([S1, S2, C1, C3, I1, I3])

            case 'C1':
                if C1 not in roles:
                    add.append(C1)
                    log(f"Giving role C1 to {member.display_name}")
                    remove.extend([S1, S2, S3, C3, I1, I3])

            case 'C3':
                if C3 not in roles:
                    add.append(C3)
                    log(f"Giving role C3 to {member.display_name}")
                    remove.extend([S1, S2, S3, C1, I1, I3])

            case 'I1':
                if I1 not in roles:
                    add.append(I1)
                    log(f"Giving role I1 to {member.display_name}")
                    remove.extend([S1, S2, S3, C1, C3, I3])

            case 'I3':
                if I3 not in roles:
                    add.append(I3)
                    log(f"Giving role I3 to {member.display_name}")
                    remove.extend([S1, S2, S3, C1, C3, I1])

        return add, remove

    async def update_user_type(self, guild, member: discord.Member, status, instructor, add, remove, roles):
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

        if status == None:
            if Guest not in roles:
                add.append(Guest)
                log(f"Giving role {Guest.name} to {member.display_name}")
                remove.extend([Home, Visit, Instructor, Mentor])
            return add, remove

        match status[0]:
            case 'home':
                if Home not in roles:
                    add.append(Home)
                    log(f"Giving role {Home.name} to {member.display_name}")
                if instructor == None:
                    remove.extend([Visit, Instructor, Mentor, Guest])
                    return add, remove
                elif instructor[0] == 0 and Mentor not in roles:
                    add.append(Mentor)
                    log(f"Giving role {Mentor.name} to {member.display_name}")
                    remove.extend([Visit, Instructor, Guest])

                elif instructor[0] == 1:
                    log("Member status home+instructor OGGA bOGGA", "error")
                    # add.append(Instructor)
                    # log(f"Giving role {Instructor.name} to {member.display_name}")
                    # remove.extend([Visit, Mentor, Guest])

            case 'visit':
                if Visit not in roles:
                    add.append(Visit)
                    log(f"Giving role {Visit.name} to {member.display_name}")
                    remove.extend([Home, Instructor, Mentor, Guest])

            case 'instructor':
                if Home not in roles:
                    add.append(Home)
                    log(f"Giving role {Home.name} to {member.display_name}")
                if Instructor not in roles:    
                    add.append(Instructor)
                    log(f"Giving role {Instructor.name} to {member.display_name}")
                    remove.extend([Visit, Guest, Mentor])

        return add, remove

    async def top_controller(self, guild, member, mycurs, add, remove, roles):
        TopRole = int(os.getenv('TOP-ROLE'))

        Top = guild.get_role(TopRole)

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {member.id}")
        user = mycurs.fetchone()

        if not user:
            return

        # mycurs.execute(f"SELECT cid FROM roster ORDER BY currency DESC LIMIT 5")
        (_, daysInMonth) = calendar.monthrange(datetime.today().year, datetime.today().month)
        dateStart = datetime.today().replace(day=1, hour=0, minute=0, second=0).isoformat('T', 'seconds')
        dateEnd = datetime.today().replace(day=daysInMonth, hour=23, minute=59, second=59).isoformat('T', 'seconds')
        # print(f"start of month: {dateStart}, end of month: {dateEnd}")

        mycurs.execute(f"""
            SELECT cid, SUM(duration) AS duration 
            FROM {os.getenv('DB-NAME')}.session_logs 
            WHERE session_start BETWEEN '{dateStart}' AND '{dateEnd}' 
            GROUP BY cid  
            ORDER BY duration DESC 
            LIMIT 5
        """)
        
        topFive = [row[0] for row in mycurs.fetchall()]  #Fetch all top controllers

        if user[0] in topFive:
            if Top not in roles:
                log("Congrats for being in the top 5...")
                add.append(Top)
        else:
            if Top in member.roles:
                log("Not a top controller anymore...")
                remove.append(Top)

        return add, remove

    async def set_nickname(self, guild, member: discord.Member, fname, lname, cid, cid_only, fullname):
        # Check if the member is the guild owner, and if so, do nothing
        if member == guild.owner:
            return member

        # Create the desired nickname based on the conditions
        if cid_only or len(f"{fname} - {cid}") > 32:
            desired_nickname = str(cid)
        elif not fullname or len(f"{fname} {lname} - {cid}") > 32:
            desired_nickname = f"{fname} - {cid}"
        else:
            desired_nickname = f"{fname} {lname} - {cid}"

        # Only update the nickname if the desired nickname is different from the current one
        if member.nick != desired_nickname:
            updated_member = await member.edit(nick=desired_nickname)
            log(f"Nickname set to {updated_member.nick}")
        else:
            log(f"Nickname for {member.display_name} is already correct, no change needed.")

        return member

    def database_connect(self):
        dbhost = os.getenv('DB-HOST')
        dbuser = os.getenv('DB-USER')
        dbpass = os.getenv('DB-PASS')
        dbname = os.getenv('DB-NAME')

        try:
            db = mariadb.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
            log("Connected to the database", "success")
            return db
        except mariadb.Error as e:
            log(f"Error connecting to MariaDB Platform: {e}", "error")
            return None

    async def remove_excess_roles(self, member, roles):
        for role in roles:
            if role in member.roles:
                await member.remove_roles(role)
                log(f"     Removing Role {role.name} to {member.display_name}")

    async def role_updater(self, member, guild, mycurs):
        verifiedRole = int(os.getenv('VERIFIED-ROLE'))
        guestRole = int(os.getenv('GUEST-ROLE'))

        Verified = guild.get_role(verifiedRole)
        Guest = guild.get_role(guestRole)

        add = []
        remove = []
        roles = member.roles

        """Updates roles for a single user using a shared DB connection"""

        mycurs.execute(
            f"SELECT id, discord_user_id, rating_short, display_cid_only, display_last_name, display_fname, lname, permissions FROM users WHERE discord_user_id = {member.id}")
        user = mycurs.fetchone()

        if not user:
            if Verified in member.roles:
                # await member.edit(roles=[Verified, Guest])
                log("Not in the Database, but Verified", "warn")
            else:
                await member.edit(roles=[Guest])
                log("Not in the Database!", "warn")

            return 0

        member = await self.set_nickname(guild, member, user[5], user[6], user[0], user[3], user[4])
        
        if Verified not in roles:
            add.append(Verified)
        if user[7] > 0:
            add, remove = await self.update_user_rating(guild, member, user[2],add,remove,roles)

        mycurs.execute(f"SELECT status FROM roster WHERE user_id = {user[0]}")
        status = mycurs.fetchone()
        mycurs.execute(f"SELECT is_instructor FROM teachers WHERE user_cid= {user[0]}")
        instructor = mycurs.fetchone()

        add, remove = await self.update_user_type(guild, member, status, instructor, add, remove, roles)
        add, remove = await self.top_controller(guild, member, mycurs, add, remove, roles)

        if add:
            await member.add_roles(*add)
        if remove:
            await self.remove_excess_roles(member, remove)
