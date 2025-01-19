import os

import discord
import mariadb as mariadb
from discord.ext import commands
from dotenv import load_dotenv

from .customlogging import log

class Website(commands.Cog):

    def __init__(self, client):
        self.client = client
        load_dotenv()
    
    @commands.hybrid_command(name='waitlist', description="Check your position on the waitlist")
    async def waitlist(self, ctx):
        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()

        if not user:
            await ctx.send(embed=discord.Embed(title="You're not in our database!", description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your Discord account in your dashboard at http://www.czvr.ca",colour = 0xF23131), ephemeral=True)
            return

        mycurs.execute("SELECT user_id FROM students WHERE status = 0")
        waitlist = mycurs.fetchall()

        mycurs.execute("SELECT wait_length FROM training_waittimes WHERE id = 1")
        waittime = mycurs.fetchone()
        mycurs.close()

        for position, person in enumerate(waitlist):
            if user[0] == person[0]:

                await ctx.send(embed=discord.Embed(title="Keep on waiting",description=f"Beep! {ctx.author.mention}, your waitlist position is **{position+1}**. Once it is your turn your instructor will reach out to you. \n\nMake sure you have emails from @vatcan.ca and @czvr.ca whitelisted in your spam filter!!\n\nThe Current wait time to start ground and delivery training is approximately **{waittime[0]}**."), ephemeral=True)
                return

        await ctx.send(embed=discord.Embed(title="You are not on the waitlist",description=f"CHIRP!! {ctx.author.mention}, you are not on our waitlist. If you beleive this is an error contact our Chief Instructor!\n\nThe current wait time in Vancouver to begin delivery and ground training is approximately **{waittime[0]}**."), ephemeral=True)

    @commands.hybrid_command(name='waittime', description="Check the current estimated wait time for new Home Controller Training")
    async def waittime(self, ctx):

        mycurs = self.database_connect()

        mycurs.execute("SELECT wait_length FROM training_waittimes WHERE id = 1")
        waittime = mycurs.fetchone()
        mycurs.close()

        await ctx.send(embed=discord.Embed(title="Current Wait Times",description=f"Beep! {ctx.author.mention}, the current wait time to begin ground and delivery training in CZVR is approximately **{waittime[0]}**."))

    @commands.hybrid_command(name='activity', description="Check how many hours you've logged this quarter")
    async def activity(self, ctx):

        mycurs = self.database_connect()

        mycurs.execute(f"SELECT id FROM users WHERE discord_user_id = {ctx.author.id}")
        user = mycurs.fetchone()

        mycurs.execute(f"SELECT staff FROM roster WHERE cid = {user[0]}")
        role = mycurs.fetchone()

        if not user:
            await ctx.send(embed=discord.Embed(title="You're not in our database!",
                                               description=f"CHIRP!! {ctx.author.mention}, you are not in our database, please link your discord account in your dashboard at http://www.czvr.ca",
                                               colour=0xF23131))
            return

        mycurs.execute(f"SELECT currency FROM roster WHERE cid = {user[0]}")
        hours = mycurs.fetchone()
        mycurs.close()

        if not hours:
            await ctx.send(embed=discord.Embed(title="You're not a Vancouver",
                                               description=f"CHIRP!! {ctx.author.mention}, it doesn't look like you are a home or visiting controller, so you have no hours in CZVR. If you are interested in become a CZVR controller do ~joinczvr. If you are interested in visiting CZVR submit a visiting request through vatcan.ca",
                                               colour=0xF23131))
            return

        if hours[0] == None:
            hours = [0.0]

        if role[0] == "exec":
            reqhrs = 3
        elif role[0] == "ins" or role[0] == "mentor" or role[0] == "staff":
            reqhrs = 3
        else:
            reqhrs = 3

        if hours[0] >= reqhrs:
            await ctx.send(embed=discord.Embed(title=f"Your activity this quarter is {hours[0]} hours! \n\n Congrats, you have met your minimum required hours this quarter: ({reqhrs} hours)."))
        elif hours[0] < reqhrs:
            await ctx.send(embed=discord.Embed(title="Not Yet Meeting Quarterly Hours",
                                               description=f"Your activity this quarter is {hours[0]}. You require a minimum of {reqhrs} hours each quarter.",
                                               colour=0xF23131))
            
        log(f"{ctx.author.nick} has {hours[0]} of {reqhrs} required hours for this quarter")

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


async def setup(client):
    await client.add_cog(Website(client))
