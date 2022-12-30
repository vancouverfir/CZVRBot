import os

import discord
import mariadb as mariadb
from discord.ext import commands
from dotenv import load_dotenv



async def setup(client):
    await client.add_cog(Updater(client))


class Updater(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()


    @commands.command()
    async def updateroles(self, ctx):

        verifiedRole = int(os.getenv('VERIFIED-ROLE'))
        guestRole = int(os.getenv('GUEST-ROLE'))


        print(f"Updating roles for {ctx.author.nick}")
        Verified = ctx.guild.get_role(verifiedRole)
        Guest = ctx.guild.get_role(guestRole)
        """Updates roles for a single user"""

        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id, discord_user_id, rating_short, display_cid_only, display_last_name, display_fname, lname FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()
        #commented out for soft launch to allow time for users to link their accounts. When ready to remove roles from unlinked accounts uncomment the below statements.
        if not user:
           # if Verified in ctx.author.roles:
           #    await ctx.author.edit(roles=[Verified,Guest])
           # else:
           #     await ctx.author.edit(roles=[])
           if ctx.command.name == 'updateroles':
               await ctx.send(
               f"CHIRP!!, {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at www.czvr.ca")
           return

        await self.set_nickname(ctx, ctx.author, user[5], user[6], user[0], user[3], user[4])
        await ctx.author.add_roles(Verified)
        await self.update_user_rating(ctx, ctx.author, user[2])

        mycurs.execute(f"SELECT status FROM roster WHERE user_id = {user[0]}")
        status = mycurs.fetchone()
        mycurs.execute(f"SELECT is_instructor FROM teachers WHERE user_cid= {user[0]}")
        instructor = mycurs.fetchone()
        await self.update_user_type(ctx, ctx.author, status[0], instructor)


        if ctx.command.name == 'updateroles':
            await ctx.send(f"{ctx.author.mention}, chirp! Your roles are now up to date!")

        mycurs.close()

        print(f"Completed updating all roles for {ctx.author.nick}\n")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def updateall(self, ctx):
        print(f"Updating all roles for all users")
        """Used to update roles for all users"""

        for member in ctx.guild.members:
            if member.bot:
                pass
            else:
                ctx.author = member
                await self.updateroles(ctx)


        await ctx.send("All roles have been updated")
        print("Completed updating all user roles\n")

    # def get_users_data(self):
    #
    #     mycurs = self.database_connect()
    #
    #     mycurs.execute("SELECT id, discord_user_id, rating_short, display_cid_only, display_last_name, display_fname, lname FROM users WHERE discord_user_id IS NOT NULL")
    #
    #     result = mycurs.fetchall()
    #     return result

    async def update_user_rating(self, ctx, member: discord.Member, rating):

        s1Role = int(os.getenv('S1-ROLE'))
        s2Role = int(os.getenv('S2-ROLE'))
        s3Role = int(os.getenv('S3-ROLE'))
        c1Role = int(os.getenv('C1-ROLE'))
        c3Role = int(os.getenv('C3-ROLE'))
        i1Role = int(os.getenv('I1-ROLE'))
        i3Role = int(os.getenv('I3-ROLE'))

        S1 = ctx.guild.get_role(s1Role)
        S2 = ctx.guild.get_role(s2Role)
        S3 = ctx.guild.get_role(s3Role)
        C1 = ctx.guild.get_role(c1Role)
        C3 = ctx.guild.get_role(c3Role)
        I1 = ctx.guild.get_role(i1Role)
        I3 = ctx.guild.get_role(i3Role)

        # await member.remove_roles(S1, S2, S3, C1, C3, I1, I3)
        match rating:
            case 'S1':
                await member.add_roles(S1)
                print(f"Giving Role S1 to {member.nick}")
                await self.remove_excess_roles(member,[S2,S3,C1,C3,I1,I3])

            case 'S2':
                await member.add_roles(S2)
                print(f"Giving Role S2 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S3, C1, C3, I1, I3])

            case 'S3':
                await member.add_roles(S3)
                print(f"Giving Role S3 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S2, C1, C3, I1, I3])

            case 'C1':
                await member.add_roles(C1)
                print(f"Giving Role C1 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S2, S3, C3, I1, I3])

            case 'C3':
                await member.add_roles(C3)
                print(f"Giving Role C3 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S2, S3, C1, I1, I3])

            case 'I1':
                await member.add_roles(I1)
                print(f"Giving Role I1 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S2, S3, C1, C3, I3])

            case 'I3':
                await member.add_roles(I3)
                print(f"Giving Role I3 to {member.nick}")
                await self.remove_excess_roles(member,[S1, S2, S3, C1, C3, I1])

    async def update_user_type(self, ctx, member: discord.Member, status, instructor):
        # Takes in database info to add home, visiting, and instructor roles

        homeRole = int(os.getenv('HOME-ROLE'))
        visitorRole = int(os.getenv('VISITOR-ROLE'))
        guestRole = int(os.getenv('GUEST-ROLE'))
        mentorRole = int(os.getenv('MENTOR-ROLE'))
        instructorRole = int(os.getenv('INSTRUCTOR-ROLE'))

        Home = ctx.guild.get_role(homeRole)
        Visit = ctx.guild.get_role(visitorRole)
        Instructor = ctx.guild.get_role(instructorRole)
        Guest = ctx.guild.get_role(guestRole)
        Mentor = ctx.guild.get_role(mentorRole)

        # await member.remove_roles(Home, Visit, Instructor, Guest, Mentor)

        match status:
            case 'home':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.nick}")
                if instructor == None:
                    await self.remove_excess_roles(member,[Visit,Instructor,Mentor,Guest])
                    return
                elif instructor[0] == 0:
                    await member.add_roles(Mentor)
                    print(f"Giving Role {Mentor.name} to {member.nick}")
                    await self.remove_excess_roles(member,[Visit,Instructor,Guest])

                elif instructor[0] == 1:
                    await member.add_roles(Instructor)
                    print(f"Giving Role {Instructor.name} to {member.nick}")
                    await self.remove_excess_roles(member,[Visit, Mentor, Guest])

            case 'visit':
                await member.add_roles(Visit)
                print(f"Giving Role {Visit.name} to {member.nick}")
                await self.remove_excess_roles(member,[Home,Instructor,Mentor,Guest])

            case 'instructor':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.nick}")
                await member.add_roles(Instructor)
                print(f"Giving Role {Instructor.name} to {member.nick}")
                await self.remove_excess_roles(member,[Visit, Guest, Mentor])

            case _:
                await member.add_roles(Guest)
                print(f"Giving Role {Guest.name} to {member.nick}")
                await self.remove_excess_roles(member,[Home,Visit,Instructor,Mentor])




    async def set_nickname(self, ctx, member: discord.Member, fname, lname, cid, cid_only, fullname):

        if member == ctx.guild.owner:
            return

        if cid_only:
            await member.edit(nick=str(cid))
        elif not fullname:
            await member.edit(nick=f"{fname} - {cid}")
        else:
            await member.edit(nick=f"{fname} {lname} - {cid}")


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
                print(f"Removing Role {role.name} to {member.nick}")

