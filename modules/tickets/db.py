import discord
from typing import TypedDict, List, Dict, Union
from utils.db import Document
from utils.embed import get_formated_embed, get_formated_field

class Qestion(TypedDict):
    question: str
    answer: str
    
class ChannelNameScheme(TypedDict):
    locked: str
    unlocked: str
class Panel(TypedDict):
    name: str
    description: str
    active: bool
    category: int
    channel: str
    emoji: str    
    question: Dict[str, Qestion]
    support_roles: List[int]
    ping_role: int
    ticket_message: str
    panel_message: int
    nameing_scheme: str

class TicketConfig(TypedDict):
    _id: int
    admin_roles: List[int]
    default_category: int
    default_channel: int
    log_channel: int
    transcript_channel: int
    panel_message: int
    panels: Dict[str, Panel]
    nameing_scheme: ChannelNameScheme

class Anonymous(TypedDict):
    status: bool
    thread_id: int


class Ticket(TypedDict):
    _id: int
    user_id: int
    panel: str
    status: str
    added_roles: List[int]
    added_users: List[int]
    channel_id: int
    anonymous: Anonymous


class TicketDB:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Tickets']
        self.config = Document(self.db, 'Config', TicketConfig)
        self.ticket = Document(self.db, 'Tickets', Ticket)

    async def create_config(self, _id:int) -> TicketConfig:
        """
        Create the config

        Args:
            _id (int): The guild id

        Returns:
            TicketConfig: The config
        """

        data: TicketConfig = {
            '_id': _id,
            'admin_roles': [],
            'default_category': None,
            'log_channel': None,
            'transcript_channel': None,
            'default_channel': None,
            'nameing_schems': None,
            'panel_message': 0,
            'panels': {},
        }
        await self.config.insert(data)
        return data

    async def get_config(self, _id:int) -> TicketConfig:
        """
        Get the config

        Args:
            _id (int): The guild id
            
        Returns:
            TicketConfig: The config
        """

        data = await self.config.find(_id)
        if not data:
            return await self.create_config(_id)
        return data

    async def update_config(self, _id:int, data:TicketConfig):
        """
        Update the config

        Args:

            _id (int): The guild id
            data (TicketConfig): The data
        """
        await self.config.update(_id, data)
    
    async def get_config_embed(self, _id: int=None, data: TicketConfig=None) -> discord.Embed:
        """
        Get the config embed

        Args:
            _id (int, optional): The guild id. Defaults to None.
            data (TicketConfig, optional): The data. Defaults to None.

        Raises:
            ValueError: No data provided

        Returns:
            discord.Embed: The embed
        """
        if all([not _id, not data]):
            raise ValueError("No data provided")
        
        if _id: data = await self.get_config(_id)

        guild = self.bot.get_guild(data['_id'])
        if not guild:
            raise ValueError("Guild not found")
        embed_arg = await get_formated_embed(["Admin Roles", "Default Category", "Log Channel", "Transcript Channel", "Default Panel Channel", "Panel Count"])
        embed = discord.Embed(description="", color=self.bot.default_color)

        embed.description = ""
        embed.description += "<:tgk_message:1113527047373979668> `Ticket General Config`\n\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_arg['Admin Roles'], data=data['admin_roles'], type='role')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_arg['Default Category'], data=data['default_category'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_arg['Default Panel Channel'], data=data['default_channel'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_arg['Log Channel'], data=data['log_channel'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_arg['Transcript Channel'], data=data['transcript_channel'], type='channel')}\n"
        embed.description += f"{embed_arg['Panel Count']}{len(data['panels'].keys())}\n"

        embed.description += "\n<:tgk_hint:1206282482744561744> Use buttons to edit the config\n"

        return embed
    
    async def panel_embed(self, guild: discord.Guild, data: Panel) -> discord.Embed:
        """
        Get the panel embed

        Args:
            guild (discord.Guild): The guild
            data (Panel): The data

        Returns:
            discord.Embed: The embed
        """

        embed_args = await get_formated_embed(["Name", "Active", "Category", "Channel", "Emoji", "Ticket Message", "Description", "Ping Role", "Support Roles", "Nameing Scheme"])
        embed = discord.Embed(description="", color=self.bot.default_color)

        embed.description = "<:tgk_create:1107262030399930428> `Ticket Panel`\n\n"

        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Active'], data=data['active'], type='bool')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Name'], data=data['name'], type='str')}\n"
        embed.description += f"{embed_args['Description']} {'<:tgk_active:1082676793342951475>' if data['description'] != None else '<:tgk_deactivated:1082676877468119110>'}\n"
        embed.description += f"{embed_args['Ticket Message']} {'<:tgk_active:1082676793342951475>' if data['ticket_message'] != None else '<:tgk_deactivated:1082676877468119110>'}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Nameing Scheme'], data=data['nameing_scheme'], type='str')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Ping Role'], data=data['ping_role'], type='role')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Support Roles'], data=data['support_roles'], type='role')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Category'], data=data['category'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Channel'], data=data['channel'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Emoji'], data=data['emoji'], type='str')}\n"

        embed.description += "\n<:tgk_hint:1206282482744561744> Use buttons to edit the panel\n"

        return embed