import discord
import io
import contextlib
import textwrap

from traceback import format_exception
from discord import app_commands
from discord.ext import commands
from typing import List
from utils.views.buttons import Confirm
from utils.checks import is_dev
from utils.converters import clean_code
from utils.paginator import Contex_Paginator

class Dev(commands.Cog, name="dev", description="Dev commands"):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_auto_complete(self, interaction: discord.Interaction, current:str) -> List[app_commands.Choice[str]]:
        _list =  [
            app_commands.Choice(name=cog, value=cog)
            for cog in interaction.client.extensions if current.lower() in cog.lower()
        ]
        return _list[:24]

    dev = app_commands.Group(name="dev", description="Dev commands")
    
    @dev.command(name="reload", description="Reloads a cog")
    @app_commands.autocomplete(cog=cog_auto_complete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_dev)
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.send_message(embed=discord.Embed(description=f"Reloading cog `{cog}`...", color=interaction.client.default_color))
        try:
            await self.bot.reload_extension(cog)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully reloaded cog `{cog}`", color=interaction.client.default_color))
        except Exception as e:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Error while reloading cog `{cog}`: {e}", color=interaction.client.default_color))

    @dev.command(name="sync", description="Syncs a guild/gobal command")
    @app_commands.check(is_dev)
    async def sync(self, interaction: discord.Interaction, guild_id: str=None):
        if guild_id is None:
            await interaction.response.send_message(embed=discord.Embed(description="Syncing global commands...", color=interaction.client.default_color))
            await interaction.tree.sync()
            await interaction.edit_original_response(embed=discord.Embed(description="Successfully synced global commands", color=interaction.client.default_color))
        else:
            guild = interaction.client.fetch_guild(int(guild_id))
            if guild is None:
                return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=interaction.client.default_color))
            await interaction.response.send_message(embed=discord.Embed(description=f"Syncing guild commands for `{guild.name}`...", color=interaction.client.default_color))
            await interaction.tree.sync(guild=guild)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully synced guild commands for `{guild.name}`", color=interaction.client.default_color))
    
    @dev.command(name="get-logs", description="Gets the logs form console")
    @app_commands.check(is_dev)
    async def get_logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(file=discord.File("./discord.log", filename="discord.log"), ephemeral=True, delete_after=120)
    
    @dev.command(name="shutdown", description="Shuts down the bot")
    @app_commands.check(is_dev)
    async def shutdown(self, interaction: discord.Interaction):
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description="Are you sure you want to shutdown the bot?", color=interaction.client.default_color), view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            await interaction.edit_original_response(embed=discord.Embed(description="Shutting down...", color=interaction.client.default_color))
            await interaction.client.close()
        else:
            await interaction.edit_original_response(embed=discord.Embed(description="Shutdown cancelled", color=interaction.client.default_color))
    
    @commands.command(name="eval", description="Evaluates a python code")
    async def _eval(self, ctx, *, code):
        if ctx.author.id not in self.bot.owner_ids:
            return await ctx.send("You are not allowed to use this command")

        code = clean_code(code)
        local_variables = {
            "discord": discord,
            "commands": commands,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        stdout = io.StringIO()
    
        try:
            with contextlib.redirect_stdout(stdout):

                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}", local_variables,
                )
                obj = await local_variables["func"]()

                result = f"{stdout.getvalue()}\n-- {obj}\n"
                
        except Exception as e:
            result = "".join(format_exception(e,e,e.__traceback__))
        page = []
        for i in range(0, len(result), 2000):
            page.append(discord.Embed(description=f'```py\n{result[i:i + 2000]}\n```', color=ctx.author.color))
        
        await Contex_Paginator(ctx, page).start(embeded=True, quick_navigation=False)

async def setup(bot):
    await bot.add_cog(Dev(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)])