import discord
from discord.ext import commands
from discord import app_commands

import logging
import logging.handlers
import os
import asyncio
import datetime

from dotenv import load_dotenv
from aiohttp import ClientSession
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from utils.db import Document
from utils.views.ticket_system import Ticket_controll

load_dotenv()
class Bot_base(commands.Bot):
    def __init__(self, intetns=discord.Intents.all(), command_prefix=commands.when_mentioned_or("-"), **options):
        super().__init__(intents=intetns, command_prefix=command_prefix, **options)
        self.remove_command("help")
    
    async def setup_hook(self) -> None:
        self.mongo = AsyncIOMotorClient(os.environ.get("MONGO"))
        self.db = self.mongo["Database"]
        
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension(f"cogs.{file[:-3]}")
        
        # await bot.tree.sync()
        # await bot.tree.sync(guild=discord.Object(999551299286732871))

bot = Bot_base(help_command=None, application_id=998152864201457754, case_insensitive=True, owner_ids=[488614633670967307, 301657045248114690], activity=discord.Activity(type=discord.ActivityType.playing, name="with discord API"), stats=discord.Status.idle)

bot.start_time = datetime.datetime.now()
bot.secret = os.environ.get("SECRET")
bot.token = os.environ.get("TOKEN")
bot.default_color = 0x36393F

@bot.event
async def on_ready():
    bot.emoji_server = bot.get_guild(991711295139233834)
    bot.add_view(Ticket_controll())
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loadded cogs: {len(bot.extensions)}")
    print(f"Cached Emoji Server: {bot.emoji_server.name} | {bot.emoji_server.id}")
    print(f"Bot Views: {len(bot.persistent_views)}")
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.playing, name="With New Features"))

@bot.tree.command(name="ping", description="Check bots leatency")
async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Ping {bot.latency*1000.0:.2f}ms"))

if __name__ == "__main__":
    bot.run(bot.token)