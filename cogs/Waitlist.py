import os

import discord
import mariadb as mariadb
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

wList = []

class Waitlist(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()
    
    @commands.command()
    async def waitlist(self, ctx):
        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()

        if not user:
            await ctx.send(
               f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca")
            return

        mycurs.execute("SELECT user_id FROM students WHERE status = 0")
        waitlist = mycurs.fetchall()



        for position, person in enumerate(waitlist):
            if user[0] == person[0]:

                await ctx.send(embed=discord.Embed(description=f"Beep! {ctx.author.mention}, your waitlist position is **{position+1}**. Once it is your turn your instructor will reach out to you. \n\nMakesure you have emails from @vatcan.ca and @czvr.ca witelisted in your spam filter!!"))
                return

        await ctx.send(embed=discord.Embed(description=f"CHIRP!! {ctx.author.mention}, you are not on our waitlist. If you beleive this is an error contact our Chief Instructor!"))


                





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



    

async def setup(client):
    await client.add_cog(Waitlist(client))
