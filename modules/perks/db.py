import datetime
from typing import List, Dict, TypedDict
from discord.ext.commands import Bot
from discord import Guild, Embed
from enum import Enum

from utils.db import Document
from utils.embed import get_formated_embed, get_formated_field


COLOR = 0x2B2D31


class RolesProfiles(TypedDict):
    RoleId: int
    Duration: int | str
    FriendLimit: int


class ChannelsProfiles(TypedDict):
    RoleId: int
    Duration: int | str
    FriendLimit: int
    TopPosition: bool


class EmojisProfiles(TypedDict):
    RoleId: int
    Duration: int | str


class HighLightsProfiles(TypedDict):
    RoleId: int
    Duration: int | str
    TriggerLimit: int


class ArsProfiles(TypedDict):
    RoleId: int
    Duration: int | str
    TriggerLimit: int


class Profiles(TypedDict):
    RolesPorfiles: Dict[str, RolesProfiles]
    ChannelsProfiles: Dict[str, ChannelsProfiles]
    HighLightsProfiles: Dict[str, HighLightsProfiles]
    ArsProfiles: Dict[str, ArsProfiles]
    EmojisProfiles: Dict[str, EmojisProfiles]

class CustomChannelSettings(TypedDict):
    CategoryName: str
    TopCategoryName: str
    ChannelPerCategory: int
    CustomCategorys: List[int]

class CustomRoleSettings(TypedDict):
    RolePossition: int
class ProfileSettings(TypedDict):
    CustomChannels: CustomChannelSettings
    CustomRoles: CustomRoleSettings

class GuildConfig(TypedDict):
    _id: int
    GuildId: int
    ModRoles: List[int]
    AdminRoles: List[int]
    LogChannel: int
    ProfileSettings: Dict[str, ProfileSettings]
    Profiles: Dict[str, Profiles]


# NOTE User Configs Types


class Ignore(TypedDict):
    Users: List[int]
    Channels: List[int]


class UserCustomRoles(TypedDict):
    RoleId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    FriendLimit: int
    Friends: List[int]
    Freezed: bool
    LastActivity: datetime.datetime


class UserCustomChannels(TypedDict):
    ChannelId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    FriendLimit: int
    Friends: List[int]
    Freezed: bool
    LastActivity: datetime.datetime


class UserCustomEmojis(TypedDict):
    EmojiId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    Freezed: bool
    LastActivity: datetime.datetime


class UserCustomHighLights(TypedDict):
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    TriggerLimit: int
    Freezed: bool
    LastActivity: datetime.datetime
    Ignore: Ignore


class ArTypes(Enum):
    Emoji = 1
    Channel = 2


class UserCustomArs(TypedDict):
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    TriggerLimit: int
    Freezed: bool
    LastActivity: datetime.datetime
    Ignore: Ignore
    Type: ArTypes


class ClaimedInfo(TypedDict):
    RoleId: int
    ClaimedAt: datetime.datetime


class Claimed(TypedDict):
    Roles: Dict[str, ClaimedInfo]
    Channels: Dict[str, ClaimedInfo]
    Emojis: Dict[str, ClaimedInfo]
    HighLights: List[int]
    Ars: Dict[str, ClaimedInfo]


class Ban(TypedDict):
    Banned: bool
    Reason: str
    BannedBy: int


class UserConfig(TypedDict):
    UserId: int
    GuildId: int
    Claimed: Claimed
    IgnoreClaimed: bool
    Banned: Ban


class Backend:
    def __init__(self, bot: Bot, CollectionName: str):
        self.db = bot.mongo[CollectionName]  # type: ignore
        self.Configs = Document(self.db, "Configs", GuildConfig)
        self.UserSettings = Document(self.db, "UserSettings", UserConfig)
        self.UserCustomRoles = Document(self.db, "UserCustomRoles", UserCustomRoles)
        self.UserCustomChannels = Document(
            self.db, "UserCustomChannels", UserCustomChannels
        )
        self.UserCustomEmojis = Document(self.db, "UserCustomEmojis", UserCustomEmojis)
        self.UserCustomHighLights = Document(
            self.db, "UserCustomHighLights", UserCustomHighLights
        )
        self.UserCustomArs = Document(self.db, "UserCustomArs", UserCustomArs)

    async def CreateGuildConfig(self, GuildId: int | Guild):
        data: GuildConfig = {
            "_id": GuildId.id if isinstance(GuildId, Guild) else GuildId,
            "GuildId": GuildId,
            "ModRoles": [],
            "AdminRoles": [],
            "LogChannel": None,
            "ProfileSettings": {
                "CustomChannels": {
                    "CategoryName": "Custom Channels",
                    "TopCategoryName": "Top Custom Channels",
                    "ChannelPerCategory": 10,
                },
                "CustomRoles": {"RolePossition": None},
            },
            "Profiles": {
                "RolesProfiles": {},
                "ChannelsProfiles": {},
                "HighLightsProfiles": {},
                "ArsProfiles": {},
                "EmojisProfiles": {},
            },
        }
        await self.Configs.insert(data)
        return data

    async def GetGuildConfig(self, GuildId: int | Guild) -> GuildConfig:
        return await self.Configs.find(
            GuildId.id if isinstance(GuildId, Guild) else GuildId
        )

    async def UpdateGuildConfig(self, GuildId: int | Guild, Data: GuildConfig):
        return await self.Configs.update(
            filter_dict={"_id": GuildId.id if isinstance(GuildId, Guild) else GuildId},
            data=Data,
        )

    async def CreateUserConfig(self, UserId: int, GuildId: int):
        return await self.UserSettings.insert(
            {
                "UserId": UserId,
                "GuildId": GuildId,
                "Claimed": {
                    "Roles": {},
                    "Channels": {},
                    "Emojis": {},
                    "HighLights": [],
                    "Ars": {},
                },
                "IgnoreClaimed": False,
            }
        )

    async def GetUserConfig(self, UserId: int, GuildId: int):
        return await self.UserSettings.find({"UserId": UserId, "GuildId": GuildId})

    async def UpdateUserConfig(self, UserId: int, GuildId: int, Data: UserConfig):
        return await self.UserSettings.update(
            filter_dict={"UserId": UserId, "GuildId": GuildId}, data=Data
        )

    async def CreateUserCustomRole(
        self,
        user_id: int,
        guild_id: int,
        role_id: int,
        duration: int | str,
        friend_limit: int,
    ):
        return await self.UserCustomRoles.insert(
            {
                "UserId": user_id,
                "GuildId": guild_id,
                "RoleId": role_id,
                "Duration": duration,
                "FriendLimit": friend_limit,
                "Friends": [],
                "Freezed": False,
                "LastActivity": datetime.datetime.utcnow(),
            }
        )

    async def GetUserCustomRoles(self, user_id: int, guild_id: int):
        return await self.UserCustomRoles.find({"UserId": user_id, "GuildId": guild_id})

    async def UpdateUserCustomRole(
        self, user_id: int, guild_id: int, role_id: int, data: UserCustomRoles
    ):
        return await self.UserCustomRoles.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id, "RoleId": role_id},
            data=data,
        )

    async def CreateUserCustomChannel(
        self,
        user_id: int,
        guild_id: int,
        channel_id: int,
        duration: int | str,
        friend_limit: int,
    ):
        return await self.UserCustomChannels.insert(
            {
                "UserId": user_id,
                "GuildId": guild_id,
                "ChannelId": channel_id,
                "Duration": duration,
                "FriendLimit": friend_limit,
                "Friends": [],
                "Freezed": False,
                "LastActivity": datetime.datetime.utcnow(),
            }
        )

    async def GetUserCustomChannels(self, user_id: int, guild_id: int):
        return await self.UserCustomChannels.find(
            {"UserId": user_id, "GuildId": guild_id}
        )

    async def UpdateUserCustomChannel(
        self, user_id: int, guild_id: int, channel_id: int, data: UserCustomChannels
    ):
        return await self.UserCustomChannels.update(
            filter_dict={
                "UserId": user_id,
                "GuildId": guild_id,
                "ChannelId": channel_id,
            },
            data=data,
        )

    async def CreateUserCustomEmoji(
        self, user_id: int, guild_id: int, emoji_id: int, duration: int | str
    ):
        return await self.UserCustomEmojis.insert(
            {
                "UserId": user_id,
                "GuildId": guild_id,
                "EmojiId": emoji_id,
                "Duration": duration,
                "Freezed": False,
                "LastActivity": datetime.datetime.utcnow(),
            }
        )

    async def GetUserCustomEmojis(self, user_id: int, guild_id: int):
        return await self.UserCustomEmojis.find(
            {"UserId": user_id, "GuildId": guild_id}
        )

    async def UpdateUserCustomEmoji(
        self, user_id: int, guild_id: int, emoji_id: int, data: UserCustomEmojis
    ):
        return await self.UserCustomEmojis.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id, "EmojiId": emoji_id},
            data=data,
        )

    async def CreateUserCustomHighLight(
        self, user_id: int, guild_id: int, duration: int | str, trigger_limit: int
    ):
        return await self.UserCustomHighLights.insert(
            {
                "UserId": user_id,
                "GuildId": guild_id,
                "Duration": duration,
                "TriggerLimit": trigger_limit,
                "Freezed": False,
                "LastActivity": datetime.datetime.utcnow(),
                "Ignore": {"Users": [], "Channels": []},
            }
        )

    async def GetUserCustomHighLights(self, user_id: int, guild_id: int):
        return await self.UserCustomHighLights.find(
            {"UserId": user_id, "GuildId": guild_id}
        )

    async def UpdateUserCustomHighLight(
        self, user_id: int, guild_id: int, data: UserCustomHighLights
    ):
        return await self.UserCustomHighLights.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id},
            data=data,
        )

    async def CreateUserCustomAr(
        self,
        user_id: int,
        guild_id: int,
        duration: int | str,
        trigger_limit: int,
        type: ArTypes,
    ):
        return await self.UserCustomArs.insert(
            {
                "UserId": user_id,
                "GuildId": guild_id,
                "Duration": duration,
                "TriggerLimit": trigger_limit,
                "Freezed": False,
                "LastActivity": datetime.datetime.utcnow(),
                "Ignore": {"Users": [], "Channels": []},
                "Type": type,
            }
        )

    async def GetUserCustomArs(self, user_id: int, guild_id: int):
        return await self.UserCustomArs.find({"UserId": user_id, "GuildId": guild_id})

    async def UpdateUserCustomAr(
        self, user_id: int, guild_id: int, data: UserCustomArs
    ):
        return await self.UserCustomArs.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id},
            data=data,
        )

    async def GetConfigEmbed(self, guild: Guild):
        Config = await self.GetGuildConfig(GuildId=guild.id)

        if Config is None:
            Config = await self.CreateGuildConfig(GuildId=guild.id)
        embed_args = await get_formated_embed(
            arguments=[
                "Admin Roles",
                "Mod Roles",
                "Log Channel",
            ],
            custom_end=":",
        )
        embed: Embed = Embed(
            color=COLOR,
            description=f"<:tgk_bank:1073920882130558987> `{guild.name} Custom Perk Settings`\n\n",
        )
        values = {
            "Admin Roles": await get_formated_field(
                name=embed_args["Admin Roles"],
                type="role",
                data=Config["AdminRoles"],
                guild=guild,
            ),
            "Mod Roles": await get_formated_field(
                name=embed_args["Mod Roles"],
                type="role",
                data=Config["ModRoles"],
                guild=guild,
            ),
            "Log Channel": await get_formated_field(
                name=embed_args["Log Channel"],
                type="channel",
                data=Config["LogChannel"],
                guild=guild,
            ),
        }

        for value in values.values():
            embed.description += f"{value}\n"
        profiles: Profiles = Config["Profiles"]
        profile_value = ""
        profile_value += f"* Role Profiles: {len(profiles['RolesProfiles'])}\n"
        profile_value += f"* Channel Profiles: {len(profiles['ChannelsProfiles'])}\n"
        profile_value += (
            f"* HighLights Profiles: {len(profiles['HighLightsProfiles'])}\n"
        )
        profile_value += f"* Ars Profiles: {len(profiles['ArsProfiles'])}\n"
        profile_value += f"* Emojis Profiles: {len(profiles['EmojisProfiles'])}\n"

        embed.add_field(name="Profiles", value=profile_value, inline=False)

        return embed
