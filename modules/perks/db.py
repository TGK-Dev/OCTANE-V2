import discord
import datetime
import enum
from typing import Union, TypedDict
from utils.embed import get_formated_embed, get_formated_field


class Freeze(TypedDict):
    friends: bool
    share_limit: bool
    delete: bool


class Activity(TypedDict):
    messages: int
    last_message: datetime.datetime
    previous_cat: int


class Custom_Channel(TypedDict):
    user_id: int
    guild_id: int
    channel_id: int
    duration: Union[int, str]
    created_at: Union[int, str]
    share_limit: int
    friend_list: list[int]
    activity: Activity
    freeze: Freeze


class Custom_Roles(TypedDict):
    user_id: int
    guild_id: int
    role_id: int
    duration: Union[int, str]
    created_at: Union[int, str]
    share_limit: int
    friend_list: list[int]
    freeze: Freeze


class Custom_React(TypedDict):
    guild_id: int
    user_id: int
    emojis: list[int]
    last_react: datetime.datetime
    max_emoji: int


class Custom_Highlight(TypedDict):
    guild_id: int
    user_id: int
    triggers: list[str]
    ignore_channel: list[int]
    ignore_users: list[int]
    last_trigger: datetime.datetime
    tigger_limit: int


class Custom_Emoji(TypedDict):
    guild_id: int
    user_id: int
    emojis: list[int]
    max_emoji: int


class Emoji_Request(TypedDict):
    _id: int
    user_id: int
    guild_id: int
    shared_limit: int
    emojis: list[int]


class Profile(TypedDict):
    role_id: int
    duration: Union[int, str]
    share_limit: int
    top_profile: bool


class Emojji_Config(TypedDict):
    max: int
    request_channel: int


class Custom_Category(TypedDict):
    name: str
    last_cat: int
    cat_list: list[int]


class Top_Category(TypedDict):
    name: str
    cat_id: int


class Config(TypedDict):
    _id: int
    custom_category: Custom_Category
    custom_roles_position: int
    top_channel_category: Top_Category
    emojis: Emojji_Config
    admin_roles: list[int]
    profiles: dict[str, Profile]


class Perk_Type(enum.Enum):
    roles = "roles"
    channels = "channels"
    reacts = "reacts"
    highlights = "highlights"
    emojis = "emojis"
    config = "config"


class Perks_DB:
    """
    A class to interact with the perk database

    Attributes
    ----------

    bot: commands.Bot
        The bot instance

    Document: class
        The document class to interact

    roles: Document
        The document for custom roles

    channel: Document
        The document for custom channels

    react: Document
        The document for custom reacts

    highlight: Document
        The document for custom highlights

    emoji: Document
        The document for custom emojis

    """

    def __init__(self, bot, Document):
        self.bot = bot
        self.db = self.bot.mongo["Perk_Database"]
        self.roles = Document(self.db, "custom_roles")
        self.channel = Document(self.db, "custom_channel")
        self.react = Document(self.db, "custom_react")
        self.highlight = Document(self.db, "custom_highlight")
        self.emoji = Document(self.db, "custom_emoji")
        self.config = Document(self.db, "config")
        self.bans = Document(self.db, "bans")
        self.emoji_request = Document(self.db, "emoji_request")
        self.cach = {"react": {}, "highlight": {}}
        self.types = Perk_Type

    async def get_data(
        self, type: Perk_Type | str, guild_id: int, user_id: int
    ) -> Union[
        Custom_Roles,
        Custom_Channel,
        Custom_React,
        Custom_Highlight,
        Custom_Emoji,
        Config,
    ]:
        """
        Get the data from the database

        Parameters
        ----------
        type: Perk_Type | str
            The type of perk to get
        guild_id: int
            The guild id
        user_id: int
            The user id

        Returns
        -------
        Union[Custom_Roles, Custom_Channel, Custom_React, Custom_Highlight, Custom_Emoji, Config]
            The data from the database

        Raises
        ------
        Exception
            If the perk type is invalid

        """
        match type:
            case Perk_Type.roles | "roles":
                return await self.roles.find({"guild_id": guild_id, "user_id": user_id})
            case Perk_Type.channels | "channels":
                return await self.channel.find(
                    {"guild_id": guild_id, "user_id": user_id}
                )
            case Perk_Type.reacts | "reacts":
                return await self.react.find({"guild_id": guild_id, "user_id": user_id})
            case Perk_Type.highlights | "highlights":
                return await self.highlight.find(
                    {"guild_id": guild_id, "user_id": user_id}
                )
            case Perk_Type.emojis | "emojis":
                return await self.emoji.find({"guild_id": guild_id, "user_id": user_id})
            case Perk_Type.config | "config":
                return await self.config.find({"_id": guild_id})
            case _:
                raise Exception("Invalid perk type")

    async def update(self, type: Perk_Type | str, data: dict) -> None:
        """
        Update the data in the database

        Parameters
        ----------
        type: Perk_Type | str
            The type of perk to update
        data: dict
            The data to update

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the perk type is invalid

        """
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.update(data["_id"], data)

            case Perk_Type.channels | "channels":
                await self.channel.update(data["_id"], data)

            case Perk_Type.reacts | "reacts":
                await self.react.update(data["_id"], data)

            case Perk_Type.highlights | "highlights":
                await self.highlight.update(data["_id"], data)

            case Perk_Type.emojis | "emojis":
                await self.emoji.update(data["_id"], data)

            case Perk_Type.config | "config":
                await self.config.update(data["_id"], data)

            case _:
                raise Exception("Invalid perk type")

    async def delete(self, type: Perk_Type | str, data: dict) -> None:
        """
        Delete the data from the database

        Parameters
        ----------
        type: Perk_Type | str
            The type of perk to delete
        data: dict
            The data to delete

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the perk type is invalid

        """

        match type:
            case Perk_Type.roles | "roles":
                await self.roles.delete(data["_id"])

            case Perk_Type.channels | "channels":
                await self.channel.delete(data["_id"])

            case Perk_Type.reacts | "reacts":
                await self.react.delete(data["_id"])

            case Perk_Type.highlights | "highlights":
                await self.highlight.delete(data["_id"])

            case Perk_Type.emojis | "emoji":
                await self.emoji.delete(data["_id"])

            case _:
                raise Exception("Invalid perk type")

    async def create(
        self,
        type: Perk_Type | str,
        user_id: int,
        guild_id: int,
        duration: Union[int, str] = None,
        share_limit: int = None,
    ) -> Union[
        Custom_Roles,
        Custom_Channel,
        Custom_React,
        Custom_Highlight,
        Custom_Emoji,
        Config,
    ]:
        """
        Create a new perk in the database

        Parameters
        ----------
        type: Perk_Type | str
            The type of perk to create
        user_id: int
            The user id
        guild_id: int
            The guild id
        duration: Union[int, str]
            The duration of the perk
        share_limit: int
            The friend limit of the perk

        Returns
        -------
        Union[Custom_Roles, Custom_Channel, Custom_React, Custom_Highlight, Custom_Emoji, Config]
            The data from the database

        Raises
        ------
        Exception
            If the perk type is invalid

        """

        match type:
            case Perk_Type.roles | "roles":
                perk_data: Custom_Roles = {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "role_id": None,
                    "duration": duration,
                    "created_at": None,
                    "share_limit": share_limit,
                    "friend_list": [],
                    "freeze": {"friends": False, "share_limit": False, "delete": False},
                }
                await self.roles.insert(perk_data)
                return perk_data

            case Perk_Type.channels | "channels":
                perk_data: Custom_Channel = {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "channel_id": None,
                    "duration": duration,
                    "created_at": None,
                    "share_limit": share_limit,
                    "friend_list": [],
                    "freeze": {"friends": False, "share_limit": False, "delete": False},
                    "activity": {
                        "messages": 0,
                        "rank": None,
                        "previous_rank": 0,
                        "cooldown": None,
                        "last_message": None,
                    },
                }
                await self.channel.insert(perk_data)
                return perk_data

            case Perk_Type.reacts | "reacts":
                perk_data: Custom_React = {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "emojis": [],
                    "last_react": None,
                    "max_emoji": share_limit if share_limit else 1,
                }
                await self.react.insert(perk_data)
                return perk_data

            case Perk_Type.highlights | "highlights":
                perk_data: Custom_Highlight = {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "triggers": [],
                    "ignore_channel": [],
                    "ignore_users": [],
                    "last_trigger": None,
                    "tigger_limit": share_limit if share_limit else 1,
                }
                await self.highlight.insert(perk_data)
                return perk_data

            case Perk_Type.emojis | "emojis":
                perk_data: Custom_Emoji = {
                    "emojis": [],
                    "max_emoji": share_limit,
                    "guild_id": guild_id,
                    "user_id": user_id,
                }
                await self.emoji.insert(perk_data)
                return perk_data

            case Perk_Type.config | "config":
                perk_config: Config = {
                    "_id": guild_id,
                    "custom_category": {"name": None, "last_cat": None, "cat_list": []},
                    "custom_roles_position": 0,
                    "admin_roles": [],
                    "emojis": {"max": 0, "request_channel": None},
                    "profiles": {
                        "roles": {},
                        "channels": {},
                        "reacts": {},
                        "highlights": {},
                        "emojis": {},
                    },
                }
                await self.config.insert(perk_config)
                return perk_config

            case _:
                raise Exception("Invalid perk type")

    async def insert(self, type: Perk_Type | str, data: dict) -> None:
        """
        Insert the data into the database

        Parameters
        ----------
        type: Perk_Type | str
            The type of perk to insert
        data: dict
            The data to insert

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the perk type is invalid
        """

        match type:
            case Perk_Type.roles | "roles":
                await self.roles.insert(data)

            case Perk_Type.channels | "channels":
                await self.channel.insert(data)

            case Perk_Type.reacts | "reacts":
                await self.react.insert(data)

            case Perk_Type.highlights | "highlights":
                await self.highlight.insert(data)

            case Perk_Type.emojis | "emojis":
                await self.emoji.insert(data)

            case _:
                raise Exception("Invalid perk type")

    async def create_cach(self) -> bool:
        """
        Create the cache for the database

        Returns
        -------
        bool
            True if the cache is created

        Returns
        -------
        bool
            True if the cache is created
        """
        configs = await self.config.get_all()
        await self.setup_reacts(configs)
        await self.setup_highlights(configs)
        return True

    async def setup_channels(self, configs: list[dict]) -> None:
        """
        Setup the channels in the cache

        Parameters
        ----------

        configs: list[dict]
            The list of configs to setup the channels

        Returns
        -------
        None
        """

        channels = await self.channel.get_all()
        self.cach["channels"] = {}
        for data in configs:
            if data["_id"] not in self.cach["channels"].keys():
                self.cach["channels"][data["_id"]] = {}

        for channel in channels:
            if channel["channel_id"] is not None:
                continue
            self.cach["channels"][channel["guild_id"]][channel["channel_id"]] = channel

    async def setup_reacts(self, configs: list[dict]) -> None:
        """
        Setup the reacts in the cache

        Parameters
        ----------
        configs: list[dict]
            The list of configs to setup the reacts

        Returns
        -------
        None
        """
        reacts = await self.react.get_all()
        self.cach["react"] = {}
        for data in configs:
            if data["_id"] not in self.cach["react"].keys():
                self.cach["react"][data["_id"]] = {}

        for react in reacts:
            self.cach["react"][react["guild_id"]][react["user_id"]] = react

    async def setup_highlights(self, configs: list[dict]) -> None:
        """
        Setup the highlights in the cache

        Parameters
        ----------
        configs: list[dict]
            The list of configs to setup the highlights

        Returns
        -------
        None
        """

        highlights = await self.highlight.get_all()
        self.cach["highlight"] = {}
        for data in configs:
            if data["_id"] not in self.cach["highlight"].keys():
                self.cach["highlight"][data["_id"]] = {}

        for highlight in highlights:
            self.cach["highlight"][highlight["guild_id"]][highlight["user_id"]] = (
                highlight
            )

    async def update_cache(
        self, perk: Perk_Type, guild: discord.Guild, data: dict
    ) -> None:
        """
        Update the cache for the database

        Parameters
        ----------
        perk: Perk_Type
            The type of perk to update

        guild: discord.Guild
            The guild to update the cache

        data: dict
            The data to update

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the perk type is invalid
        """

        match perk:
            case Perk_Type.reacts:
                self.cach["react"][guild.id][data["user_id"]] = data
            case Perk_Type.highlights:
                self.cach["highlight"][guild.id][data["user_id"]] = data
            case _:
                raise Exception("Invalid perk type")

    async def get_config_embed(
        self, guild: discord.Guild, config: Config = None
    ) -> discord.Embed:
        """
        Get the config embed for the guild

        Parameters
        ----------
        guild: discord.Guild
            The guild to get the config embed

        config: Config(Optional)
            The config to use to get the embed

        Returns
        -------
        discord.Embed
            The config embed for the guild
        """

        if not config:
            config: Config = await self.get_data(
                Perk_Type.config, guild.id, guild.owner_id
            )
        formated_args = await get_formated_embed(
            [
                "Admin Roles",
                "Custom Roles Position",
                "Custom Channel Category",
                "Top Channel Category",
                "Max Emojis",
                "Request Channel",
            ]
        )

        embed = discord.Embed(description="", color=self.bot.default_color)
        embed.description = ""

        embed.description += "<:level_roles:1123938667212312637> `Perks`"
        embed.description += "\n\n"

        embed.description += f"{await get_formated_field(guild=guild,name=formated_args['Admin Roles'], type='role', data=config['admin_roles'])}\n"
        embed.description += f"{await get_formated_field(guild=guild,name=formated_args['Custom Roles Position'], type='role', data=config['custom_roles_position'])}\n"
        embed.description += f"{await get_formated_field(guild=guild,name=formated_args['Custom Channel Category'], type='str', data=config['top_channel_category']['name'])}\n"
        embed.description += f"{formated_args['Max Emojis']}{config['emojis']['max']}\n"
        embed.description += f"{await get_formated_field(guild=guild,name=formated_args['Request Channel'], type='channel', data=config['emojis']['request_channel'])}\n"

        embed.description += f"{formated_args['Custom Channel Category']}{len(config['custom_category']['cat_list'])}\n\n"

        embed.description += "<:tgk_category:1076602579846447184> `Profiles List`\n\n"
        profile_formated_args = await get_formated_embed(
            ["Roles", "Channels", "Reacts", "Highlights", "Emojis"]
        )
        embed.description += f"{profile_formated_args['Roles']} {len(config['profiles']['roles'].keys())}\n"
        embed.description += f"{profile_formated_args['Channels']} {len(config['profiles']['channels'].keys())}\n"
        embed.description += f"{profile_formated_args['Reacts']} {len(config['profiles']['reacts'].keys())}\n"
        embed.description += f"{profile_formated_args['Highlights']} {len(config['profiles']['highlights'].keys())}\n"
        embed.description += f"{profile_formated_args['Emojis']} {len(config['profiles']['emojis'].keys())}\n\n"

        embed.description += (
            "<:tgk_hint:1206282482744561744> Use buttons below to changes the settings"
        )

        return embed

    async def calulate_profile(
        self, type: Perk_Type, guild: discord.Guild, user: discord.Member
    ) -> dict:
        """
        Calculate the profile for the user

        Parameters
        ----------
        type: Perk_Type
            The type of perk to calculate
        guild: discord.Guild
            The guild to calculate the profile
        user: discord.Member
            The user to calculate the profile

        Returns
        -------
        dict
            The profile for the user
        """

        config: Config = await self.get_data(Perk_Type.config, guild.id, guild.owner_id)
        profile = config["profiles"][type.value]
        user_roles = [role.id for role in user.roles]
        share_limit = 0
        duration = 0
        for key, value in profile.items():
            if int(key) in user_roles:
                share_limit += value["share_limit"]
                if value["duration"] == "permanent":
                    duration = "permanent"

        return {"share_limit": share_limit, "duration": duration}
