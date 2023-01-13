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

load_dotenv()
class Bot_base(commands.Bot):
    def __init__(self, intetns=discord.Intents.all(), command_prefix=commands.when_mentioned_or("-"), **options):
        super().__init__(intents=intetns, command_prefix=command_prefix, **options)
        self.remove_command("help")
    
    async def setup_hook(self) -> None:
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension(f"cogs.{file[:-3]}")
        #await bot.tree.sync()
    

bot = Bot_base(help_command=None, application_id=998152864201457754, case_insensitive=True, owner_ids=[488614633670967307], activity=discord.Activity(type=discord.ActivityType.playing, name="with discord API"), stats=discord.Status.idle)

async def main():

    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename="bot.log",
        encoding="utf-8",
        maxBytes=32*1024*1024,
        backupCount=5
    )
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', style="{")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    async with ClientSession():
        async with bot:
            bot.mongo = AsyncIOMotorClient(os.environ.get("MONGO"))
            bot.db = bot.mongo["tgk_database"]
            await bot.start(os.environ.get("TOKEN"))

bot.start_time = datetime.datetime.now()

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loadded cogs: {len(bot.extensions)}")

@bot.tree.command(name="ping", description="Check bots leatency")
async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Ping {bot.latency*1000.0:.2f}ms"))

if __name__ == "__main__":
    asyncio.run(main())