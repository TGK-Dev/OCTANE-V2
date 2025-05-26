import discord
from discord import app_commands, Interaction
from discord.ext import commands
from .db import Config, TeamMember, Queue, Backend
from .view import QueueView


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class TeamModule(commands.GroupCog, name="team"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._backend = Backend(bot)
        self.bot._team = self._backend
        self.bot.add_view(QueueView())

    staff = app_commands.Group(
        name="staff",
        description="Staff commands for team events",
    )

    manage = app_commands.Group(
        name="manage", description="Manage team events and configurations"
    )

    async def interaction_check(self, interaction: Interaction) -> bool:
        config = await self._backend.get_config(interaction.guild.id)
        if not interaction.user.guild_permissions.administrator:
            user_roles = [role.id for role in interaction.user.roles]
            if (set(config["staff_roles"]) & set(user_roles)) == set():
                await interaction.response.send_message(
                    "You do not have permission to use this command.", ephemeral=True
                )
                return False
        return True

    @manage.command(name="add", description="Add a team to the event")
    @app_commands.describe(team_name="The name of the team to add")
    async def add_team(
        self, interaction: Interaction, team_name: str, role: discord.Role
    ):
        config = await self._backend.get_config(interaction.guild.id)
        if team_name not in config["teams"]:
            config["teams"][team_name] = {
                "total_points": 0,
                "team_name": team_name,
                "team_role": role.id,
            }
            await self._backend.config.update(interaction.guild.id, config)
            await interaction.response.send_message(
                f"Team {team_name} added with role {role.name}.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Team {team_name} already exists.", ephemeral=True
            )

    @staff.command(name="add", description="Add a staff role for team events")
    @app_commands.describe(role="The role to add as a staff role")
    async def add_staff_role(self, interaction: Interaction, role: discord.Role):
        config = await self._backend.get_config(interaction.guild.id)
        if role.id not in config["staff_roles"]:
            config["staff_roles"].append(role.id)
            await self._backend.config.update(interaction.guild.id, config)
            await interaction.response.send_message(
                f"Role {role.name} added as a staff role.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Role {role.name} is already a staff role.", ephemeral=True
            )

    @staff.command(name="remove", description="Remove a staff role for team events")
    @app_commands.describe(role="The role to remove from staff roles")
    async def remove_staff_role(self, interaction: Interaction, role: discord.Role):
        config = await self._backend.get_config(interaction.guild.id)
        if role.id in config["staff_roles"]:
            config["staff_roles"].remove(role.id)
            await self._backend.config.update(interaction.guild.id, config)
            await interaction.response.send_message(
                f"Role {role.name} removed from staff roles.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Role {role.name} is not a staff role.", ephemeral=True
            )

    @staff.command(name="point", description="Add/remove points to a team")
    @app_commands.describe(points="Points to add", member="Member to add points to")
    async def add_points(
        self, interaction: Interaction, points: int, member: discord.Member
    ):
        config = await self._backend.get_config(interaction.guild.id)
        player = await self._backend.get_player(member.id)
        team = config["teams"].get(player["team"], None)
        if not team:
            await interaction.response.send_message(
                f"Invalid team for {member.display_name}.", ephemeral=True
            )
            return
        player["points"] += points
        team["total_points"] += points
        await self._backend.update_player(member.id, player)
        await self._backend.config.update(interaction.guild.id, config)
        await interaction.response.send_message(
            f"Added {points} points to {member.display_name} in team {team['team_name']}.",
            ephemeral=True,
        )

    @staff.command(name="queue", description="send the queue view")
    async def queue_view(self, interaction: Interaction):
        embed = discord.Embed(
            title="Join the Event Queue",
            description="Click the button below to join the event queue teams will be assigned randomly.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(
            embed=embed, view=QueueView(), ephemeral=False
        )

    @app_commands.command(name="stats", description="Get a player's stats")
    @app_commands.describe(member="The member to get stats for")
    async def stats(self, interaction: Interaction, member: discord.Member):
        player = await self._backend.get_player(member.id)
        if not player:
            await interaction.response.send_message(
                f"No stats found for {member.display_name}.", ephemeral=True
            )
            return
        config = await self._backend.get_config(interaction.guild.id)
        team = config["teams"].get(player["team"], None)
        embed = discord.Embed(
            title=f"{member.display_name}'s Stats",
            description=f"Team: {team['team_name'] if team else 'No Team'}\n"
            f"Points: {player['points']} \n Team Points: {team['total_points'] if team else 0}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamModule(bot), guilds=[discord.Object(1334016396228689961)])
