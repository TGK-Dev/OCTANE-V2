import discord
from typing import TypedDict, List, Dict, Union
from utils.db import Document

class Panel(TypedDict):
    name: str
    description: str
    category: int
    qestions: Dict[str, str]
    support_roles: List[int]
    ticket_message: str
    

class TicketConfig(TypedDict):
    _id: int
    admin_roles: List[int]
    default_category: int
    log_channel: int
    transcript_channel: int
    panel_message: int
    panels: Dict[str]


class Anonymous(TypedDict):
    status: bool
    thread_id: int


class Ticket(TypedDict):
    _id: int
    user_id: int
    panel: str
    status: str
    support_roles: List[int]
    support_users: List[int]
    channel_id: int
    anonymous: Anonymous


class TicketDB:
    def __init__(self, bot):
        self.db = bot.mongo['Tickets']
        self.config = Document(self.db, 'Config', TicketConfig)
        self.tickets = Document(self.db, 'Tickets', Ticket)

    async def create_config(self, _id:int) -> TicketConfig:
        data: TicketConfig = {
            '_id': _id,
            'admin_roles': [],
            'default_category': 0,
            'log_channel': 0,
            'transcript_channel': 0,
            'panel_message': 0,
            'panels': {}
        }

    async def get_config(self, _id:int) -> TicketConfig:
        data = await self.config.find(_id)
        if not data:
            return await self.create_config(_id)
        return data

    async def update_config(self, _id:int, data:TicketConfig):
        await self.config.update(_id, data)
    
    async def get_config_embed(self, _id: int=None, data: TicketConfig=None) -> discord.Embed:
        if not data or not _id:
            raise ValueError("You must provide either _id or data")