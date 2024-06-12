import discord
from discord.ext import commands
import logging
import os
import asyncio
import datetime
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import io
import chat_exporter

load_dotenv()

discord.utils.setup_logging(root=True, level=logging.INFO)


class Botbase(commands.Bot):
    def __init__(self, application_id, sync: bool = False):
        super().__init__(
            intents=discord.Intents.all(),
            command_prefix=".",
            description="A Bot for server management",
            case_insensitive=False,
            owner_ids=[488614633670967307, 301657045248114690],
            activity=discord.Activity(type=discord.ActivityType.custom, name="Startup"),
            status=discord.Status.offline,
            help_command=None,
            application_id=application_id,
        )
        self.default_color = 0x2B2D31
        self.start_time = datetime.datetime.now()
        self.sync = sync
        self.token = os.environ.get("TEST_TOKEN")
        self.secret = os.environ.get("TEST_SECRET")
        self.connection_url = "mongodb://localhost:27017/"
        self.connection_url2 = os.environ.get("ACE_DB")
        self.restart = False
        self.mongo = AsyncIOMotorClient(self.connection_url)
        self.db = self.mongo["Database"]
        self.aceDb = AsyncIOMotorClient(self.connection_url2)
        self.db2 = self.aceDb["TGK"]
        self.emoji_server: discord.Guild | None = None

    async def setup_hook(self):
        for file in os.listdir("./cogs"):
            if (
                file.endswith(".py")
                and not file.startswith("_")
                and file.startswith(("dev", "serversettings", "basic"))
            ):
                await self.load_extension(f"cogs.{file[:-3]}")

    #     for folder in os.listdir("./modules"):
    #         if folder == "notepad":
    #             for file in os.listdir(f"./modules/{folder}"):
    #                 if file == "module.py":
    #                     await self.load_extension(f"modules.{folder}.{file[:-3]}")


bot = Botbase(998152864201457754, False)

tree = bot.tree

token = os.environ.get("TEST_TOKEN")


async def main():
    await bot.start(os.environ.get("TEST_TOKEN"))


@bot.command(name="export")
async def export(ctx):
    message = [message async for message in ctx.channel.history(limit=20)]
    file = await chat_exporter.raw_export(channel=ctx.channel, messages=message)
    await ctx.send(file=discord.File(io.BytesIO(file.encode()), filename="chat.html"))


@bot.event
async def on_ready():
    await bot.tree.sync()
    for guild in bot.guilds:
        await bot.tree.sync(guild=guild)
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loaded cogs: {len(bot.extensions)}")
    # print(f"Cached Emoji Server: {bot.emoji_server.name} | {bot.emoji_server.id}")
    print(f"Bot Views: {len(bot.persistent_views)}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Over Server Security"
        ),
        status=discord.Status.offline,
    )

    await bot.tree.sync()


@bot.tree.command(name="ping", description="Check bots latency")
async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(
        content=None,
        embed=discord.Embed(description=f"Ping {bot.latency * 1000.0:.2f}ms"),
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id == 461441940496580622:
        return
    await bot.process_commands(message)


asyncio.run(main())
if bot.restart:
    os.system("cls")
    os.system("python dev.py")
