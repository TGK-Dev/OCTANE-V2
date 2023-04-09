import discord
from discord.ext import commands
from discord import app_commands

import os
import asyncio
import datetime
import logging
import logging.handlers
import aiohttp

from io import BytesIO
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from utils.converters import dict_to_tree


load_dotenv()
discord.utils.setup_logging(
    level=logging.INFO,
    formatter=logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'),
    handler=logging.handlers.RotatingFileHandler(filename='discord.log',encoding='utf-8',maxBytes=32 * 1024 * 1024)
    )


class Bot_base(commands.Bot):
    def __init__(self, application_id, sync:bool=False):
        super().__init__(intents=discord.Intents.all(), command_prefix=commands.when_mentioned_or("-"),description="A Bot for server management", case_insensitive=False, owner_ids=[488614633670967307, 301657045248114690], activity=discord.Activity(type=discord.ActivityType.playing, name="Startup"),status=discord.Status.idle, help_command=None, application_id=application_id)
        self.default_color = 0x2b2d31
        self.start_time = datetime.datetime.now()    
        self.sync = sync
        self.token = os.environ.get("TOKEN")
        self.secret = os.environ.get("SECRET")
        self.connection_url = os.environ.get("MONGO")
        self.connection_url2 = os.environ.get("ACE_DB")
    
    async def setup_hook(self):
        self.mongo = AsyncIOMotorClient(self.connection_url)
        self.db = self.mongo["Database"]
        
        self.aceDb = AsyncIOMotorClient(self.connection_url2)
        self.db2 = self.aceDb["TGK"]
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension(f"cogs.{file[:-3]}")
            
        if self.sync == True:
            await self.tree.sync()
            await self.tree.sync(guild=discord.Object(999551299286732871))
            await self.tree.sync(guild=discord.Object(785839283847954433))
        self.emoji_server = await self.fetch_guild(991711295139233834)


bot = Bot_base(816699167824281621, False)

tree = bot.tree
async def main():
    await bot.start(bot.token)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loadded cogs: {len(bot.extensions)}")
    print(f"Cached Emoji Server: {bot.emoji_server.name} | {bot.emoji_server.id}")
    print(f"Bot Views: {len(bot.persistent_views)}")
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Over Server Security"), status=discord.Status.dnd)

@bot.tree.command(name="ping", description="Check bots leatency")
async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Ping {bot.latency*1000.0:.2f}ms"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id == 461441940496580622:
        return
    await bot.process_commands(message)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        return await interaction.response.send_message(f"Please wait {error.retry_after:.2f} seconds before trying again.", ephemeral=True, delete_after=10)
    else:
        embed = discord.Embed(description=f"```\n{error}\n```", color=bot.default_color)
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            await interaction.followup.send(embed=embed, ephemeral=True)

    tree_format = interaction.data.copy()
    tree_format = dict_to_tree(tree_format)

    embed = discord.Embed(title="Error", color=bot.default_color)
    embed.add_field(name="Interaction Data Tree", value=f"```yaml\n{tree_format}\n```", inline=False)
    embed.add_field(name="Channel", value=f"{interaction.channel.mention} | {interaction.channel.id}", inline=False)
    embed.add_field(name="Guild", value=f"{interaction.guild.name} | {interaction.guild.id}", inline=False)
    embed.add_field(name="Author", value=f"{interaction.user.mention} | {interaction.user.id}", inline=False)
    embed.add_field(name="Command", value=f"{interaction.command.name if interaction.command else 'None'}", inline=False)

    error_traceback = ""
    #add whole trace back
    error_traceback += f"{error}\n"
    buffer = BytesIO(error_traceback.encode('utf-8'))
    file = discord.File(buffer, filename=f"Error-{interaction.command.name}.log")
    buffer.close()

    url = "https://canary.discord.com/api/webhooks/1076590771542708285/88D3SRMTYHPe4copSvTQ451KXx7Tk2WDsRYUPN4wtVI1qQbqDmyn0eAiUOhV7XW8SO3G"

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(url, session=session)
        await webhook.send(embed=embed, avatar_url=interaction.client.user.avatar.url if interaction.client.user.avatar else interaction.client.user.default_avatar, username=f"{interaction.client.user.name}'s Error Logger", file=file)

asyncio.run(main())
