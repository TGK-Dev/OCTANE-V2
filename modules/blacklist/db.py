from typing import List, Dict, TypedDict
from enum import Enum
import datetime
from utils.db import Document
import discord

class ProfileType(Enum):
    Normal = 0
    Strike = 1

    def __str__(self):
        return self.name

class Profile(TypedDict):
    _id: str
    create_by: int
    create_at: datetime.datetime
    role_add: List[int]
    role_remove: List[int]
    reason: str | None
    type: ProfileType | str
    strike_limit: int
    strike_expire: int    

class Config(TypedDict):
    _id: int
    mod_roles: List[int]
    profiles: Dict[str, Profile]
    log_channel: int

class Strike(TypedDict):
    Strike_at: datetime.datetime
    Strike_expire: datetime.datetime
    Strike_by: int
    Strike_reason: str

class StrikeUser(TypedDict):
    user_id: int
    guild_id: int
    profile: str
    strikes: List[Strike]

class Blacklist(TypedDict):
    user_id: int
    guild_id: int
    profile: str
    Blacklist_at: datetime.datetime
    Blacklist_by: int
    Blacklist_reason: str
    Blacklist_duration: int
    Blacklist_end: datetime.datetime

class backend:
    def __init__(self, bot):
        self.db = bot.mongo["Blacklist"]
        self.config = Document(self.db, "config")
        self.blacklist = Document(self.db, "blacklist")
        self.strike = Document(self.db, "strike")
        self.config_cache: Dict[Dict] = {}

    async def setup(self):
        for guild in await self.config.get_all():
            self.config_cache[guild["_id"]] = Config(**guild)

    async def create_config(self, guild_id: int) -> Config:
        config: Config = {
            "_id": guild_id,
            "mod_roles": [],
            "profiles": {},
            "log_channel": None
        }
        config = await self.config.insert(config)
        self.config_cache[guild_id] = config
        return config

    async def get_config(self, guild_id: int) -> Config:
        if guild_id in self.config_cache.keys():
            return self.config_cache[guild_id]
        else:
            data = await self.config.find(guild_id)
            if data is None:
                return await self.create_config(guild_id)
            else:
                return Config(**data)

    async def update_config(self, guild_id: int, data: Config | dict ):
        if isinstance(data, dict):
            data = Config(**data)
        await self.config.update(guild_id, data)
        self.config_cache[guild_id] = data

    async def get_blacklist(self, user: discord.Member, profile: Profile) -> Blacklist:
        data = await self.blacklist.find({"user_id": user.id, "profile": profile.id, "guild_id": user.guild.id})
        if not data:
            return None
        del data["_id"]
        return Blacklist(**data)

    async def insert_blacklist(self, data: Blacklist):
        await self.blacklist.insert(data)