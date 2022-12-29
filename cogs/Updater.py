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

        dbhost = os.getenv('DB-HOST')
        dbuser = os.getenv('DB-USER')
        dbpass = os.getenv('DB-PASS')
        dbname = os.getenv('DB-NAME')

        try:
            db = mariadb.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
        else:
            self.mycurs = db.cursor()

    @commands.command()
    async def updateroles(self, ctx):
        print(f"Updating roles for {ctx.author.name}")
        """Updates roles for a single user"""

        self.mycurs.execute(f"SELECT id, rating_short FROM users WHERE discord_user_id = {ctx.author.id}")
        user = self.mycurs.fetchone()
        if not user:
            await ctx.send(
                "You are not in our database, please link your discord account in your dashboard at www.czvr.ca")
            return

        await self.update_user_rating(ctx, ctx.author, user[1])

        self.mycurs.execute(f"SELECT status FROM roster WHERE user_id = {user[0]}")
        status = self.mycurs.fetchone()
        await self.update_user_type(ctx, ctx.author, status[0])

        print(f"Completed updating all roles for {ctx.author.name}\n")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def updateall(self, ctx):
        print(f"Updating all roles for all users")
        """Used to update roles for all users"""
        users = self.get_users_data()
        for user in users:
            member = ctx.guild.get_member(user[2])
            await self.update_user_rating(ctx, member, user[1])
            self.mycurs.execute(f"SELECT status FROM roster WHERE user_id = {user[0]}")
            status = self.mycurs.fetchone()
            await self.update_user_type(ctx, member, status[0])

        print("Completed updating all user roles\n")

    def get_users_data(self):

        self.mycurs.execute("SELECT id, rating_short, discord_user_id FROM users WHERE discord_user_id IS NOT NULL")

        result = self.mycurs.fetchall()
        return result

    async def update_user_rating(self, ctx, member: discord.Member, rating):
        S1 = ctx.guild.get_role(1057518699000627210)
        S2 = ctx.guild.get_role(765205927019806800)
        S3 = ctx.guild.get_role(765205897873719306)
        C1 = ctx.guild.get_role(765205868421185597)
        C3 = ctx.guild.get_role(765205815337549834)
        I1 = ctx.guild.get_role(1057761149929652265)
        I3 = ctx.guild.get_role(1057761172427915325)

        await member.remove_roles(S1, S2, S3, C1, C3, I1, I3)
        match rating:
            case 'S1':
                await member.add_roles(S1)
                print(f"Giving Role S1 to {member.name}")

            case 'S2':
                await member.add_roles(S2)
                print(f"Giving Role S2 to {member.name}")

            case 'S3':
                await member.add_roles(S3)
                print(f"Giving Role S3 to {member.name}")

            case 'C1':
                await member.add_roles(C1)
                print(f"Giving Role C1 to {member.name}")

            case 'C3':
                await member.add_roles(C3)
                print(f"Giving Role C3 to {member.name}")

            case 'I1':
                await member.add_roles(I1)
                print(f"Giving Role I1 to {member.name}")

            case 'I3':
                await member.add_roles(I3)
                print(f"Giving Role I3 to {member.name}")

    async def update_user_type(self, ctx, member: discord.Member, status):
        # Takes in database info to add home, visiting, and instructor roles
        Home = ctx.guild.get_role(1057798306614485093)
        Visit = ctx.guild.get_role(1057798314592043110)
        Instructor = ctx.guild.get_role(1057798317653897236)
        Guest = ctx.guild.get_role(1057798557811355810)

        await member.remove_roles(Home, Visit, Instructor, Guest)

        match status:
            case 'home':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.name}")

            case 'visit':
                await member.add_roles(Visit)
                print(f"Giving Role {Visit.name} to {member.name}")

            case 'instructor':
                await member.add_roles(Home)
                print(f"Giving Role {Home.name} to {member.name}")
                await member.add_roles(Instructor)
                print(f"Giving Role {Instructor.name} to {member.name}")

            case _:
                await member.add_roles(Guest)
