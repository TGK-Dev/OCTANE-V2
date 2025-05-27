from utils.db import Document
from typing import TypedDict


class TeamMember(TypedDict):
    id: int
    team: str
    points: int


class Team(TypedDict):
    total_points: int
    team_name: str
    team_role: int


class Config(TypedDict):
    id: int
    staff_roles: list[int]
    teams: dict[str, Team]


class Queue(TypedDict):
    id: int


class Backend:
    """
    Perameters
    ----------
    bot: commands.Bot
        The bot
    """

    def __init__(self, bot):
        self._bot = bot
        self._db = bot.mongo["Willo_team_Events"]
        self.config = Document(self._db, "Config", Config)
        self.players = Document(self._db, "Players", TeamMember)
        self.queues = Document(self._db, "Queues", Queue)

    async def get_config(self, guild_id: int) -> Config:
        """
        Returns the team event configuration.

        Returns: Config
            The team event configuration.
        """
        config = await self.config.find(guild_id)
        if not config:
            config = {
                "_id": guild_id,
                "staff_roles": [],
                "teams": {},
            }
            await self.config.insert(config)
        return config

    async def get_player(self, player_id: int) -> TeamMember:
        """
        Returns the team event player data.
        Returns: TeamMember
            The team event player data.
        """
        player = await self.players.find(player_id)
        if not player:
            return None
        return player

    async def update_player(self, player_id: int, data: TeamMember) -> None:
        """
        Updates the team event player data.

        Parameters
        ----------
        player_id: int
            The ID of the player.
        data: TeamMember
            The data to update for the player.
        """
        await self.players.update(player_id, data)

    async def get_team(self, team_name: str) -> None | list[TeamMember]:
        """
        Returns the team event team data.

        Parameters
        ----------
        team_name: str
            The name of the team.

        Returns: Team
            The team event team data.
        """
        data = await self.players.find_many_by_custom("team", team_name)
        if not data:
            return None
        return data
