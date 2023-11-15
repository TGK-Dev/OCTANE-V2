import discord
from discord import app_commands, Interaction
from discord.ext import commands
import random

class Games(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.event_inprogress = False


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if message.guild is None: return
        if message.guild.id not in [999551299286732871, 785839283847954433]:
            return
        
        if self.event_inprogress: return
        if not random.random() < 0.3:
            return

        self.event_inprogress = True
         

        
        
    