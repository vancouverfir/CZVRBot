import os
import sys
from enum import Enum

import discord
import mariadb as mariadb
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

guild = None
S1 = None
S2 = None
S3 = None
C1 = None
C3 = None

async def setup(client):
    await client.add_cog(Updater(client))

class Updater(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def update(self, ctx):
        S1 = ctx.guild.get_role(1057518699000627210)
        S2 = ctx.guild.get_role(765205927019806800)
        S3 = ctx.guild.get_role(765205897873719306)
        C1 = ctx.guild.get_role(765205868421185597)
        C3 = ctx.guild.get_role(765205815337549834)
        I1 = ctx.guild.get_role(1057761149929652265)
        I3 = ctx.guild.get_role(1057761172427915325)
        """Used to delete the last messages. (Default is 5 including the command)"""
        users = self.get_users()
        for user in users:
            member = ctx.guild.get_member(user[2])
            await member.remove_roles(S1, S2, S3, C1, C3, I1, I3)
            if user[1] == 'S1':
                await member.add_roles(S1)
                print(f"Giving Role S1 to {member.name}")

            elif user[1] == 'S2':
                await member.add_roles(S2)
                print(f"Giving Role S2 to {member.name}")

            elif user[1] == 'S3':
                await member.add_roles(S3)
                print(f"Giving Role S3 to {member.name}")

            elif user[1] == 'C1':
                await member.add_roles(C1)
                print(f"Giving Role C1 to {member.name}")

            elif user[1] == 'C3':
                await member.add_roles(C3)
                print(f"Giving Role C3 to {member.name}")

            elif user[1] == 'I1':
                await member.add_roles(I1)
                print(f"Giving Role I1 to {member.name}")

            elif user[1] == 'I3':
                await member.add_roles(I3)
                print(f"Giving Role I3 to {member.name}")

    def get_users(self):
        load_dotenv()

        dbhost = os.getenv('DB-HOST')
        dbuser = os.getenv('DB-USER')
        dbpass = os.getenv('DB-PASS')
        dbport = int(os.getenv('DB-PORT'))
        dbname = os.getenv('DB-NAME')

        try:
            db = mariadb.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            sys.exit(1)

        mycurs = db.cursor()

        mycurs.execute("SELECT id, rating_short, discord_user_id FROM users WHERE discord_user_id IS NOT NULL")

        result = mycurs.fetchall()
        return result



