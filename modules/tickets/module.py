import discord
from discord.ext import commands
from discord import app_commands, Interaction
from .db import TicketDB
from .view import TicketConfig_View

class Ticket(commands.GroupCog, name="ticket"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = TicketDB(bot)
        self.bot.tickets = self.backend

    
    @app_commands.command(name="setup", description="Setup the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: Interaction):
        embed = await self.backend.get_config_embed(interaction.guild_id)
        data = await self.backend.get_config(interaction.guild_id)
        view = TicketConfig_View(user=interaction.user, data=data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()



async def setup(bot):
    await bot.add_cog(Ticket(bot))