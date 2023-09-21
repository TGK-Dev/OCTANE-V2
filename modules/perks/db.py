import discord
import enum
from discord.ext import commands
from typing import Union

class Perk_Type(enum.Enum):
    roles = "roles"
    channels = "channels"
    reacts = "reacts"
    highlights = "highlights"
    config = "config"

class Perks_DB:
    def __init__(self, bot, Document):
        self.bot = bot
        self.db = self.bot.mongo["Perk_Database"]
        self.roles = Document(self.db, "custom_roles")
        self.channel = Document(self.db, "custom_channel")
        self.react = Document(self.db, "custom_react")
        self.highlight = Document(self.db, "custom_highlight")
        self.config = Document(self.db, "config")
        self.bans = Document(self.db, "bans")
        self.cach = {'react': {}, 'highlight': {}}
        self.types = Perk_Type
    
    async def get_data(self, type: Perk_Type | str, guild_id: int, user_id: int):
        match type:
            case Perk_Type.roles | "roles":
                return await self.roles.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.channels | "channels":
                return await self.channel.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.reacts | "reacts":
                return await self.react.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.highlights | "highlights":
                return await self.highlight.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.config | "config":
                return await self.config.find({'_id': guild_id})
            case _:
                raise Exception("Invalid perk type")
    
    async def update(self, type: Perk_Type | str , data: dict):
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.update(data['_id'], data)

            case Perk_Type.channels | "channels":
                await self.channel.update(data['_id'], data)

            case Perk_Type.reacts | "reacts":
                await self.react.update(data['_id'], data)

            case Perk_Type.highlights | "highlights":
                await self.highlight.update(data['_id'], data)

            case Perk_Type.config | "config":
                await self.config.update(data['_id'], data)

            case _:
                raise Exception("Invalid perk type")

    async def delete(self, type: Perk_Type | str, data: dict):
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.delete(data['_id'])

            case Perk_Type.channels | "channels":
                await self.channel.delete(data['_id'])

            case Perk_Type.reacts | "reacts":
                await self.react.delete(data['_id'])

            case Perk_Type.highlights | "highlights":
                await self.highlight.delete(data['_id'])

            case _:
                raise Exception("Invalid perk type")

    async def create(self, type: Perk_Type | str, user_id: int, guild_id: int, duration: Union[int, str]=None, friend_limit: int=None):
        match type:
            case Perk_Type.roles | "roles":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'role_id': None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': []}
                await self.roles.insert(perk_data)
                return perk_data
            
            case Perk_Type.channels | "channels":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'channel_id':None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': [], 'activity': {'messages': 0, 'rank': None, 'previous_rank': 0, 'cooldown': None}}
                await self.channel.insert(perk_data)
                return perk_data
            
            case Perk_Type.reacts | "reacts":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'emojis': [], 'last_react': None, 'max_emoji': friend_limit if friend_limit else 1}
                await self.react.insert(perk_data)
                return perk_data

            case Perk_Type.highlights | "highlights":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'triggers': [], 'ignore_channel':[], 'ignore_users': [], 'last_trigger': None, 'tigger_limit': friend_limit if friend_limit else 1}
                await self.highlight.insert(perk_data)
                return perk_data
            
            case Perk_Type.config | "config":
                perk_config = {'_id': guild_id,'custom_category': {'name': None, 'last_cat': None, 'cat_list': []},'custom_roles_position': 0, 'admin_roles': [], "profiles": {"roles": {}, "channels": {}, "reacts": {}, "highlights": {}}}
                await self.config.insert(perk_config)
                return perk_config
            
            case _:
                raise Exception("Invalid perk type")
    
    async def insert(self, type: Perk_Type | str, data: dict):
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.insert(data)
            
            case Perk_Type.channels | "channels":
                await self.channel.insert(data)
            
            case Perk_Type.reacts | "reacts":
                await self.react.insert(data)

            case Perk_Type.highlights | "highlights":
                await self.highlight.insert(data)

            case _:
                raise Exception("Invalid perk type")
    
    async def create_cach(self):
        configs = await self.config.get_all()
        await self.setup_reacts(configs)
        await self.setup_highlights(configs)
        return True
    
    async def setup_channels(self, configs: list[dict]):
        channels = await self.channel.get_all()
        self.cach['channels'] = {}
        for data in configs:
            if data['_id'] not in self.cach['channels'].keys():
                self.cach['channels'][data['_id']] = {}
        
        for channel in channels:
            if channel['channel_id'] == None: continue
            self.cach['channels'][channel['guild_id']][channel['channel_id']] = channel
    
    async def setup_reacts(self, configs: list[dict]):
        reacts = await self.react.get_all()
        self.cach['react'] = {}
        for data in configs:
            if data['_id'] not in self.cach['react'].keys():
                self.cach['react'][data['_id']] = {}
        
        for react in reacts:
            self.cach['react'][react['guild_id']][react['user_id']] = react
    
    async def setup_highlights(self, configs: list[dict]):
        highlights = await self.highlight.get_all()
        self.cach['highlight'] = {}
        for data in configs:
            if data['_id'] not in self.cach['highlight'].keys():
                self.cach['highlight'][data['_id']] = {}
        
        for highlight in highlights:
            self.cach['highlight'][highlight['guild_id']][highlight['user_id']] = highlight

    async def update_cache(self, perk: Perk_Type, guild: discord.Guild, data: dict):
        match perk:
            case Perk_Type.reacts:
                self.cach['react'][guild.id][data['user_id']] = data
            case Perk_Type.highlights:
                self.cach['highlight'][guild.id][data['user_id']] = data
            case _:
                raise Exception("Invalid perk type")