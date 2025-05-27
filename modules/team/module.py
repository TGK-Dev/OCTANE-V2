import discord
from discord import app_commands, Interaction
from discord.ext import commands
from .db import Config, TeamMember, Queue, Backend
from .view import QueueView


@app_commands.guild_only()
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
        if interaction.command.name in ["lb", "stats"]:
            return True
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
            description="You'll be assigned a team randomly. Join below if you wish to participate to earn rewards of bots like dank, karuta and sofi!!\n\n-# PS: Rank up the contributors lb to earn individual rewards while competing for the team!",
            color=0xE6B2BA,
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
        embed = discord.Embed(color=0xE6B2BA, description="")
        embed.set_author(
            name=f"{member.display_name}'s Stats",
            icon_url=member.display_avatar.url if member.display_avatar else None,
        )
        embed.description += (
            f"<:W_dropdown2:1376381988180721706> Team: {player['team']}\n"
        )
        embed.description += (
            f"<:W_dropdown2:1376381988180721706> Points: {player['points']}\n"
        )
        embed.description += f"<:W_dropdown:1376381917926260846> Total Points : {team['total_points'] if team else 0}\n"
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @staff.command(name="endqueue", description="End the queue and assign teams")
    async def end_queue(self, interaction: Interaction):
        await interaction.response.send_message(
            "Ending the queue and assigning teams...", ephemeral=True
        )

        config = await self._backend.get_config(interaction.guild.id)
        team1 = config["teams"]["IRIS"]
        team2 = config["teams"]["ASTER"]

        team1_role = interaction.guild.get_role(team1["team_role"])
        team2_role = interaction.guild.get_role(team2["team_role"])

        await interaction.edit_original_response(
            content="Got the teams, assigning members to teams..."
        )

        queued_memebers = await self._backend.queues.get_all()
        # divide members randomly into two teams with queued members
        if len(queued_memebers) < 2:
            await interaction.response.send_message(
                "Not enough members in the queue to form teams.", ephemeral=True
            )
            return
        team1_members = []
        team2_members = []

        await interaction.edit_original_response(
            content="Dividing members into teams, please wait..."
        )

        for member in queued_memebers:
            if len(team1_members) <= len(team2_members):
                team1_members.append(member)
            else:
                team2_members.append(member)

        if len(team1_members) == 0 or len(team2_members) == 0:
            await interaction.response.send_message(
                "Not enough members in the queue to form teams.", ephemeral=True
            )
            return

        for member in team1_members:
            player = {
                "_id": member["_id"],
                "team": "IRIS",
                "points": 0,
            }
            await self._backend.players.upsert(member["_id"], player)
            member = interaction.guild.get_member(member["_id"])
            if member:
                await member.add_roles(team1_role, reason="Assigned to IRIS team")

        for member in team2_members:
            player = {
                "_id": member["_id"],
                "team": "ASTER",
                "points": 0,
            }
            await self._backend.players.upsert(member["_id"], player)
            member = interaction.guild.get_member(member["_id"])
            if member:
                await member.add_roles(team2_role, reason="Assigned to ASTER team")

        await interaction.edit_original_response(
            embed=discord.Embed(
                title="Teams Assigned",
                description=f"Team IRIS: {len(team1_members)} members\nTeam ASTER: {len(team2_members)} members",
                color=0xE6B2BA,
            ),
            content=None,
        )

    @app_commands.command(name="lb", description="Get the leaderboard for the event")
    async def leaderboard(self, interaction: Interaction):
        config = await self._backend.get_config(interaction.guild.id)
        team1 = config["teams"]["IRIS"]
        team2 = config["teams"]["ASTER"]

        team1_points = team1["total_points"] if team1 else 0
        team2_points = team2["total_points"] if team2 else 0

        team1_players = await self._backend.players.find_many_by_custom(
            {"team": "IRIS"}
        )
        team2_players = await self._backend.players.find_many_by_custom(
            {"team": "ASTER"}
        )

        if team1_players == [] or team2_players == []:
            await interaction.response.send_message(
                "No players found for the teams.", ephemeral=True
            )
            return
        team1_players = sorted(
            team1_players, key=lambda x: int(x["points"]), reverse=True
        )[:5]
        team2_players = sorted(
            team2_players, key=lambda x: int(x["points"]), reverse=True
        )[:5]

        embed = discord.Embed(color=0xE6B2BA, description="")
        embed.set_author(
            name="Willow's 1k Celebration",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        iris_top = [
            interaction.guild.get_member(player["_id"])
            for player in team1_players
            if interaction.guild.get_member(player["_id"])
        ]
        aster_top = [
            interaction.guild.get_member(player["_id"])
            for player in team2_players
            if interaction.guild.get_member(player["_id"])
        ]

        iris_value = "\nTop Contributors:\n"
        if len(iris_top) < 5 or len(aster_top) < 5:
            await interaction.response.send_message(
                "Not enough players in one of the teams to display the leaderboard.",
                ephemeral=True,
            )
            return
        iris_value += f"🥇{iris_top[0].name} {team1_players[0]['points']}\n"
        iris_value += f"🥈{iris_top[1].name} {team1_players[1]['points']}\n"
        iris_value += f"🥉{iris_top[2].name} {team1_players[2]['points']}\n"
        iris_value += f"<:W_dropdown2:1376381988180721706> {iris_top[3].name} {team1_players[3]['points']}\n"
        iris_value += f"<:W_dropdown:1376381917926260846> {iris_top[4].name} {team1_players[4]['points']}\n\n"

        embed.add_field(
            name=f"<:W_iris:1376477418138898492> Team IRIS Total Points: {team1_points}",
            value=iris_value,
            inline=False,
        )

        aster_value = "\nTop Contributors:\n"
        aster_value += f"🥇{aster_top[0].name} {team2_players[0]['points']}\n"
        aster_value += f"🥈{aster_top[1].name} {team2_players[1]['points']}\n"
        aster_value += f"🥉{aster_top[2].name} {team2_players[2]['points']}\n"
        aster_value += f"<:W_dropdown2:1376381988180721706> {aster_top[3].name} {team2_players[3]['points']}\n"
        aster_value += f"<:W_dropdown:1376381917926260846> {aster_top[4].name} {team2_players[4]['points']}\n"

        embed.add_field(
            name=f"<:W_aster:1376476650295787581> Team ASTER Total Points: {team2_points}",
            value=aster_value,
            inline=False,
        )

        embed.description += "# <:W_iris:1376477418138898492> IRIS vs <:W_aster:1376476650295787581>  ASTER Leaderboard\n"

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamModule(bot), guilds=[discord.Object(1334016396228689961)])
