from utils.db import Document
from typing import TypedDict, List, Dict
from enum import Enum

class ReactRoleMenuType(Enum):
    """
    Perameters
    ----------
    ADD_ONLY: int
        The user can only add roles
    REMOVE_ONLY: int
        The user can only remove roles
    ADD_AND_REMOVE: int
        The user can add and remove roles
    DEFAULT: int
    """
    ADD_ONLY = 0
    REMOVE_ONLY = 1
    ADD_AND_REMOVE = 2
    DEFAULT = 3
    UNIQUE = 4

    def __str__(self):
        """
        Perameters
        ----------
        type: ReactRoleMenuType
            The type to convert
        Returns: str
            The converted type
        """
        if self == self.ADD_ONLY:
            return "Add Only"
        elif self == self.REMOVE_ONLY:
            return "Remove Only"
        elif self == self.ADD_AND_REMOVE:
            return "Add and Remove"
        elif self == self.DEFAULT:
            return "Default"
        else:
            raise ValueError(f"Invalid type {self}")
    
    @classmethod
    def from_str(cls, type: str):
        """
        Perameters
        ----------
        type: str
            The type to convert
        Returns: ReactRoleMenuType
            The converted type
        """
        if type == "Add Only":
            return cls.ADD_ONLY
        elif type == "Remove Only":
            return cls.REMOVE_ONLY
        elif type == "Add and Remove":
            return cls.ADD_AND_REMOVE
        else:
            return cls.DEFAULT

class RoleMenuRoles(TypedDict):
    """
    Perameters
    ----------
    role_id: int
        The id of the role
    emoji: str
        The emoji to be used in buttons and embeds
    """
    role_id: int
    emoji: str

class RoleMenuProfile(TypedDict):
    """
    Perameters
    ----------
    name: str
        The name of the profile
    display_name: str
        The display name of the profile
    req_role_id: int
        The id of the role required to use the profile
    bl_role_id: int
        The id of the role that is blacklisted from using the profile
    type: ReactRoleMenuType
        The type of the profile
    roles: List[RoleMenuRoles]
        The roles for the profile
    """

    name: str
    display_name: str
    req_roles: List[int]
    bl_roles: List[int]
    type: ReactRoleMenuType
    roles: Dict[int, RoleMenuRoles]


class RoleMenu(TypedDict):
    """
    Perameters
    ----------
    guild_id: int
        The id of the guild
    enabled: bool
        If the role menu is enabled
    max_profiles: int
        The max amount of profiles a user can have
    roles: Dict[str, RoleMenuProfile]
        The profiles for the role menu
    """
    _id: int
    guild_id: int
    enabled: bool
    max_profiles: int
    roles: Dict[str, RoleMenuProfile]

class Backend:
    """
    Perameters
    ----------
    bot: commands.Bot
        The bot
    """
    
    def __init__(self, bot):
        self._bot = bot
        self._db = bot.mongo["RoleMenus"]
        self.Profile = Document(self._db, "Profiles", RoleMenu)
        self.Cach = Dict[int, RoleMenu]

    async def get_config(self, guild_id: int) -> RoleMenu:
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        Returns: RoleMenu
            The role menu config
        -------
        """
        if guild_id in self.Cach.keys():
            config = self.Cach[guild_id]
        else:
            config: RoleMenu = await self.fetch_config(guild_id)
            if config is None:
                config = RoleMenu(_id=guild_id,guild_id=guild_id, enabled=False, max_profiles=5, roles={})
                await self.Profile.insert(config)
            self.Cach[guild_id] = config
        return config
    
    async def fetch_config(self, guild_id: int) -> RoleMenu:
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        Returns: RoleMenu
            The role menu config
        -------
        """

        config: RoleMenu = await self.Profile.find(guild_id)
        if config is None:
            config = RoleMenu(guild_id=guild_id, enabled=False, max_profiles=5, roles={})
            await self.Profile.insert(config)
        return config

    
    async def get_profiles(self, guild_id: int) -> RoleMenu:
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        Returns: RoleMenuProfile
            The role menu config
        """
        config: RoleMenu = await self.get_config(guild_id)
        self.Cach[guild_id] = config
        return config['roles']
    
    
    async def get_profile(self, guild_id: int, name: str=None) -> RoleMenuProfile | None:
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        name: str
            The name of the profile
        Returns: RoleMenuProfile
            The role menu config
        """

        config: RoleMenu = await self.get_config(guild_id)
        self.Cach[guild_id] = config
        if isinstance(name, str):
            if name in config['roles'].keys():
                return config['roles'][name]
            else:
                return None
        else:
            return config['roles']
            
        
    
    async def update_profile(self, guild_id: int, name: str, profile: RoleMenuProfile):
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        name: str
            The name of the profile
        profile: RoleMenuProfile
            The profile to update
        """
        config: RoleMenu = await self.get_config(guild_id)
        config['roles'][name] = profile
        await self.Profile.update(config)
        self.Cach[guild_id] = config

    async def delete_profile(self, guild_id: int, name: str):
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        name: str
            The name of the profile
        """
        config: RoleMenu = await self.get_config(guild_id)
        del config['roles'][name]
        await self.Profile.update(config)
        self.Cach[guild_id] = config

    async def create_profile(self, guild_id: int, name: str):
        """
        Perameters
        ----------
        guild_id: int
            The id of the guild
        name: str
            The name of the profile
        """
        config: RoleMenu = await self.get_config(guild_id)
        config['roles'][name] = RoleMenuProfile(name=name, req_roles=[], bl_roles=[], type=ReactRoleMenuType.DEFAULT.value, roles=[])
        await self.Profile.update(config)
        self.Cach[guild_id] = config
    
    async def load(self):
        """ Loads all the configs into the cache for faster access"""
        self.Cach = {}
        for config in await self.Profile.get_all():
            config = RoleMenu(**config)
            self.Cach[config['_id']] = config
        return self.Cach





    

