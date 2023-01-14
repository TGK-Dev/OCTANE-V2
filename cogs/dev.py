import discord
from discord import app_commands
from discord.ext import commands
from typing import List

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
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.send_message(embed=discord.Embed(description=f"Reloading cog `{cog}`...", color=discord.Color.green()))
        try:
            await self.bot.reload_extension(cog)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully reloaded cog `{cog}`", color=discord.Color.green()))
        except Exception as e:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Error while reloading cog `{cog}`: {e}", color=discord.Color.red()))

async def setup(bot):
    await bot.add_cog(Dev(bot), guilds=[discord.Object(999551299286732871)])