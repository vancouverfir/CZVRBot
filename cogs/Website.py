import os

import discord
import mariadb as mariadb
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

class Website(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()
    
    @commands.command()
    async def waitlist(self, ctx):
        """Checks your position on the waitlist"""
        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()

        if not user:
            await ctx.send(embed=discord.Embed(title="You're not in our database!", description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca",colour = 0xF23131))
            return

        mycurs.execute("SELECT user_id FROM students WHERE status = 0")
        waitlist = mycurs.fetchall()

        mycurs.execute("SELECT wait_length FROM training_waittimes WHERE id = 1")
        waittime = mycurs.fetchone()



        for position, person in enumerate(waitlist):
            if user[0] == person[0]:

                await ctx.send(embed=discord.Embed(title="Keep on waiting",description=f"Beep! {ctx.author.mention}, your waitlist position is **{position+1}**. Once it is your turn your instructor will reach out to you. \n\nMake sure you have emails from @vatcan.ca and @czvr.ca whitelisted in your spam filter!!\n\nThe Current wait time to start ground and delivery training is approximately **{waittime[0]}**."))
                return

        await ctx.send(embed=discord.Embed(title="You are not on the waitlist",description=f"CHIRP!! {ctx.author.mention}, you are not on our waitlist. If you beleive this is an error contact our Chief Instructor!\n\nThe Current waitlist in vancouver to begin delivery and ground training is approximately **{waittime[0]}**."))

    @commands.command()
    async def waittime(self, ctx):
        '''Gets the current estimated wait time for new home controller training'''

        mycurs = self.database_connect()

        mycurs.execute("SELECT wait_length FROM training_waittimes WHERE id = 1")
        waittime = mycurs.fetchone()

        await ctx.send(embed=discord.Embed(title="Current Wait Times",description=f"Beep! {ctx.author.mention}, the current wait time to begin ground and delivery training in CZVR is approximately **{waittime[0]}**."))





    @commands.command()
    async def activity(self, ctx):
        '''Gets your monthly controlling hours'''

        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()

        if not user:
            await ctx.send(embed=discord.Embed(title="You're not in our database!",
                                               description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca",
                                               colour=0xF23131))
            return

        mycurs.execute(f"SELECT currency FROM roster WHERE cid = {user[0]}")
        hours = mycurs.fetchone()

        if not hours:
            await ctx.send(embed=discord.Embed(title="You're not a Vancouver",
                                               description=f"CHIRP!! {ctx.author.mention}, it doesn't look like you are a home or visiting controller, so you have no hours in CZVR. If you are interested in become a CZVR controller do ~joinczvr. If you are interested in visiting CZVR submit a visiting request through vatcan.ca",
                                               colour=0xF23131))
            return

        if hours[0] == None:
            hours = [0.0]

        await ctx.send(embed=discord.Embed(title=f"Your activity this month is {hours[0]} hours!"))

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
    await client.add_cog(Website(client))
