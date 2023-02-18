import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from utils.views.buttons import Confirm
from utils.checks import is_dev

class Dev(commands.GroupCog, name="dev", description="Dev commands"):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_auto_complete(self, interaction: discord.Interaction, current:str) -> List[app_commands.Choice[str]]:
        _list =  [
            app_commands.Choice(name=cog, value=cog)
            for cog in interaction.client.extensions if current.lower() in cog.lower()
        ]
        return _list[:24]
    
    @app_commands.command(name="reload", description="Reloads a cog")
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

    @app_commands.command(name="sync", description="Syncs a guild/gobal command")
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
    
    @app_commands.command(name="get-logs", description="Gets the logs form console")
    @app_commands.check(is_dev)
    async def get_logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(file=discord.File("./discord.log", filename="discord.log"), ephemeral=True, delete_after=120)
    
    @app_commands.command(name="shutdown", description="Shuts down the bot")
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

async def setup(bot):
    await bot.add_cog(Dev(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)])