import discord
from discord.ext import commands
from discord import app_commands

import os
import asyncio
import datetime
import logging
import logging.handlers

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv()
discord.utils.setup_logging(
    level=logging.INFO,
    formatter=logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'),
    handler=logging.handlers.RotatingFileHandler(filename='discord.log',encoding='utf-8',maxBytes=32 * 1024 * 1024)
    )


class Bot_base(commands.Bot):
    def __init__(self, application_id, sync:bool=False):
        super().__init__(intents=discord.Intents.all(), command_prefix=commands.when_mentioned_or("-"),description="A Bot for server management", case_insensitive=False, owner_ids=[488614633670967307, 301657045248114690], activity=discord.Activity(type=discord.ActivityType.watching, name="Over Server Security"),status=discord.Status.dnd, help_command=None, application_id=application_id)
        self.default_color = 0x2b2d31
        self.start_time = datetime.datetime.now()    
        self.sync = sync
    
    async def setup_hook(self):
        self.mongo = AsyncIOMotorClient(self.connection_url)
        self.db = self.mongo["Database"]
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension(f"cogs.{file[:-3]}")
            
        if self.sync == True:
            await self.tree.sync()
            await self.tree.sync(guild=discord.Object(999551299286732871))
            await self.tree.sync(guild=discord.Object(785839283847954433))
        self.emoji_server = await self.fetch_guild(991711295139233834)

bot = Bot_base(998152864201457754, False)
bot.secret = os.environ.get("SECRET")
bot.token = os.environ.get("TOKEN")
bot.connection_url = os.environ.get("MONGO")    

async def main():
    await bot.start(bot.token)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loadded cogs: {len(bot.extensions)}")
    print(f"Cached Emoji Server: {bot.emoji_server.name} | {bot.emoji_server.id}")
    print(f"Bot Views: {len(bot.persistent_views)}")

@bot.tree.command(name="ping", description="Check bots leatency")
@app_commands.checks.cooldown(1, 5)
async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Ping {bot.latency*1000.0:.2f}ms"))

asyncio.run(main())
