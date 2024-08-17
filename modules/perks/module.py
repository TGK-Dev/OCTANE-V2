from discord.ext import commands
from discord import app_commands, Interaction

from .db import Backend
from .views import PerksConfigPanel


class Perks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Backend(bot=bot, CollectionName="Perks")
        self.bot.perks = self.db

    perk = app_commands.Group(
        name="perk", description="Manage your Private custom perks"
    )
    _perks = app_commands.Group(
        name="perks", description="Manage your server members private custom perks"
    )

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            message = "You don't have the required permissions to run this command."
        else:
            message = f"An error occurred: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @staticmethod
    def _ModCheck():
        async def _ModRoleCheck(interaction: Interaction):
            if (
                interaction.user.guild_permissions.administrator
                or interaction.user.id in interaction.client.owner_ids
            ):
                return True
            db: Backend = interaction.client.perks
            config = await db.GetGuildConfig(interaction.guild)
            if not config:
                return False
            if config["ModRole"]:
                user_roles = [role.id for role in interaction.user.roles]
                if set(set(config["ModRole"]) & set(user_roles)):
                    return True
            return False

        return app_commands.check(_ModRoleCheck)

    @staticmethod
    def _AdminCheck():
        async def _AdminRoleCheck(interaction: Interaction):
            if (
                interaction.user.guild_permissions.administrator
                or interaction.user.id in interaction.client.owner_ids
            ):
                return True
            return False

        return commands.check(_AdminRoleCheck)

    @_perks.command(name="setup", description="Setup the perks for the server")
    @_AdminCheck()
    async def _perks_setup(self, interaction: Interaction):
        config = await self.db.GetGuildConfig(interaction.guild)
        embed = await self.db.GetConfigEmbed(interaction.guild)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()
        


async def setup(bot: commands.Bot):
    await bot.add_cog(Perks(bot))
