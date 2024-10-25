import datetime
import discord
from discord.ext.commands import Bot
from discord import Guild, Embed, Interaction, Role, Attachment

import aiohttp
from colour import Color
from enum import Enum
from typing import List, Dict, TypedDict

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


class ActivitySettings(TypedDict):
    Time: int
    Messages: int


class CustomChannelSettings(TypedDict):
    CategoryName: str
    TopCategoryName: str
    ChannelPerCategory: int
    TopCategory: int
    DefaultRoles: List[int]
    Activity: dict[str, ActivitySettings]
    CustomCategorys: List[int]


class CustomRoleSettings(TypedDict):
    RolePossition: int
    Activity: dict[str, ActivitySettings]


class CustomEmojiSettings(TypedDict):
    TotalCustomEmojisLimit: int


class ProfileSettings(TypedDict):
    CustomChannels: CustomChannelSettings
    CustomRoles: CustomRoleSettings
    CustomEmoji: CustomEmojiSettings


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

class Activity(TypedDict):
    LastMessage: datetime.datetime
    MessageCount: int

class UserCustomRoles(TypedDict):
    RoleId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    FriendLimit: int
    Friends: List[int]
    Freezed: bool
    Activity: dict[str, Activity]


class UserCustomChannels(TypedDict):
    ChannelId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    FriendLimit: int
    Friends: List[int]
    Freezed: bool
    Activity: dict[str, Activity]


class UserCustomEmojis(TypedDict):
    EmojiId: int
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    Freezed: bool


class UserCustomHighLights(TypedDict):
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    TriggerLimit: int
    Freezed: bool
    LastTrigger: datetime.datetime
    Ignore: Ignore


class ArTypes(Enum):
    Reaction = "Reaction"
    Message = "Message"


class Triggers(TypedDict):
    Type: ArTypes
    Content: str


class UserCustomArs(TypedDict):
    UserId: int
    GuildId: int
    Duration: int | str
    CreatedAt: int
    TriggerLimit: int
    Triggers: List[Triggers]
    Freezed: bool
    LastTrigger: datetime.datetime
    Ignore: Ignore


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
        self.ar_cache = {}
        self.hl_cache = {}

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
                    "TopCategory": None,
                    "DefaultRoles": [],
                    "Activity": {
                        "Time": 0,
                        "Messages": 0,
                    },
                },
                "CustomRoles": {
                    "RolePossition": None,
                    "Activity": {
                        "Time": 0,
                        "Messages": 0,
                    },
                },
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

    async def CreateUserSettings(self, user_id: int, guild_id: int) -> UserConfig:
        userConfig: UserConfig = {
            "UserId": user_id,
            "GuildId": guild_id,
            "Claimed": {
                "Roles": {},
                "Channels": {},
                "Emojis": {},
                "HighLights": [],
                "Ars": {},
            },
            "IgnoreClaimed": False,
            "Banned": {"Banned": False, "Reason": "", "BannedBy": None},
        }
        await self.UserSettings.insert(userConfig)
        return userConfig

    async def GetUserSettings(self, user_id: int, guild_id: int):
        userData = await self.UserSettings.find(
            {"UserId": user_id, "GuildId": guild_id}
        )
        if userData is None:
            userData = await self.CreateUserSettings(user_id, guild_id)
        return userData

    async def UpdateUserSettings(self, user_id: int, guild_id: int, data: UserConfig):
        return await self.UserSettings.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id},
            data=data,
        )

    # NOTE: Custom Role Related Functions

    async def CreateUserCustomRole(self, data: UserCustomRoles):
        data = await self.UserCustomRoles.insert(data)
        return data

    async def UpdateUserCustomRole(
        self, user_id: int, guild_id: int, role_id: int, data: UserCustomRoles
    ):
        return await self.UserCustomRoles.update(
            filter_dict={"UserId": user_id, "GuildId": guild_id, "RoleId": role_id},
            data=data,
        )

    async def GetUserCustomRoles(self, user_id: int, guild_id: int):
        return await self.UserCustomRoles.find({"UserId": user_id, "GuildId": guild_id})

    async def DeleteUserCustomRole(self, user_id: int, guild_id: int, role_id: int):
        return await self.UserCustomRoles.delete(
            {"UserId": user_id, "GuildId": guild_id, "RoleId": role_id}
        )

    async def CreateCustomRole(
        self,
        name: str,
        color: str,
        guild: Guild,
        config: GuildConfig,
        interaction: Interaction,
        role_icon: Attachment = None,
    ) -> Role | tuple[bool, str]:
        if "AmariMod" in name:
            return (False, "You can't create a role with that name")
        if len(name) > 100:
            return (False, "Role name can't be more than 100 characters")
        if len(color.replace("#", "")) != 6:
            return (False, "Color must be a hex code")
        if not color.startswith("#"):
            return (False, "Color must be a hex code starting with #")

        display_icon = None
        if role_icon:
            if not role_icon.filename.endswith(("png", "jpg", "jpeg")):
                return (False, "Role icon must be a png, jpg or jpeg file")

            async with aiohttp.ClientSession() as session:
                async with session.get(role_icon.url) as response:
                    if response.status != 200:
                        return (False, "Failed to download the role icon")
                    display_icon = await response.read()

        color = tuple(round(c * 255) for c in Color(color).rgb)
        color = discord.Color.from_rgb(*color)

        role = await guild.create_role(
            name=name,
            color=color,
            reason=f"Custom Role Claimed By {interaction.user.name}",
            display_icon=display_icon,
        )

        role_position = None
        guild = await interaction.client.fetch_guild(guild.id)
        position_role = guild.get_role(
            config["ProfileSettings"]["CustomRoles"]["RolePossition"]
        )
        if position_role:
            role_position = position_role.position

        role = guild.get_role(role.id)
        role = await role.edit(position=role_position + 1)

        return role

    async def ModifyCustomRole(
        self,
        role: discord.Role,
        interaction: discord.Interaction,
        name: str = None,
        color: str = None,
        role_icon: Attachment = None,
    ):
        keywords = {}
        if name:
            if "AmariMod" in name:
                return (False, "You can't create a role with that name")
            if len(name) > 100:
                return (False, "Role name can't be more than 100 characters")
            keywords["name"] = name

        if color:
            if len(color.replace("#", "")) != 6:
                return (False, "Color must be a hex code")
            if not color.startswith("#"):
                return (False, "Color must be a hex code starting with #")
            color = tuple(round(c * 255) for c in Color(color).rgb)
            color = discord.Color.from_rgb(*color)
            keywords["color"] = color

        if role_icon:
            if not role_icon.filename.endswith(("png", "jpg", "jpeg")):
                return (False, "Role icon must be a png, jpg or jpeg file")

            async with aiohttp.ClientSession() as session:
                async with session.get(role_icon.url) as response:
                    if response.status != 200:
                        return (False, "Failed to download the role icon")
                    display_icon = await response.read()
            keywords["display_icon"] = display_icon

        await role.edit(**keywords)
        return role

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

        embed.set_footer(
            text="Make sure to save your changes if made any",
            icon_url="https://cdn.discordapp.com/emojis/1206282482744561744.webp?quality=lossless",
        )

        return embed

    # NOTE: Custom Channel Related Functions

    async def CreateUserCustomChannel(self, data: UserCustomChannels):
        data = await self.UserCustomChannels.insert(data)
        return data

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

    async def GetUserCustomChannels(self, user_id: int, guild_id: int):
        return await self.UserCustomChannels.find(
            {"UserId": user_id, "GuildId": guild_id}
        )

    async def DeleteUserCustomChannel(
        self, user_id: int, guild_id: int, channel_id: int
    ):
        return await self.UserCustomChannels.delete(
            {"UserId": user_id, "GuildId": guild_id, "ChannelId": channel_id}
        )

    async def CreateCustomChannel(
        self,
        name: str,
        guild: Guild,
        config: GuildConfig,
        interaction: Interaction,
        top_cat: bool = False,
    ) -> discord.TextChannel | tuple[bool, str]:
        settings: CustomChannelSettings = config["ProfileSettings"]["CustomChannels"]
        category = None
        if top_cat:
            category = guild.get_channel(settings["TopCategory"])
            if not category:
                category = await guild.create_category_channel(
                    name=settings["TopCategoryName"],
                    reason=f"Top Custom Channel Category Created By {interaction.user.name}",
                    position=0,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(
                            view_channel=False
                        ),
                    },
                )
                config["ProfileSettings"]["CustomChannels"]["TopCategory"] = category.id
                await self.UpdateGuildConfig(GuildId=guild.id, Data=config)
        if settings["CustomCategorys"] == [] or category is None:
            category = await guild.create_category_channel(
                name=f"{settings['CategoryName']} - 1",
                reason=f"Custom Channel Category Created By {interaction.user.name}",
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                },
            )
            config["ProfileSettings"]["CustomChannels"]["CustomCategorys"] = [
                category.id
            ]
            await self.UpdateGuildConfig(GuildId=guild.id, Data=config)
        elif category is None:
            for category_id in settings["CustomCategorys"]:
                cat = guild.get_channel(category_id)
                if len(cat.text_channels) >= settings["ChannelPerCategory"]:
                    category = category
                    break
            if category is None:
                category = await guild.create_category_channel(
                    name=f"{settings['CategoryName']} - {len(settings['CustomCategorys']) + 1}",
                    reason=f"Custom Channel Category Created By {interaction.user.name}",
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(
                            view_channel=False
                        ),
                    },
                )
                config["ProfileSettings"]["CustomChannels"]["CustomCategorys"].append(
                    category.id
                )
                await self.UpdateGuildConfig(GuildId=guild.id, Data=config)

        overWrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, manage_permissions=True
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
            ),
        }
        for role_id in settings["DefaultRoles"]:
            role = guild.get_role(role_id)
            if role:
                overWrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    add_reactions=True,
                    external_emojis=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                )
            else:
                settings["DefaultRoles"].remove(role_id)
                await self.UpdateGuildConfig(GuildId=guild.id, Data=config)

        channel = await guild.create_text_channel(
            name=name,
            category=category,
            overwrites=overWrites,
            topic=f"Custom Channel Created By {interaction.user.name}",
        )

        return channel

    async def ModifyCustomChannel(
        self,
        channel: discord.TextChannel,
        name: str = None,
    ):
        keywords = {}
        if name:
            keywords["name"] = name

        await channel.edit(**keywords)
        return channel

    # NOTE: Custom React Related Functions

    async def CreateUserCustomReact(self, data: UserCustomArs):
        data = await self.UserCustomArs.insert(data)
        return data

    async def UpdateUserCustomReact(
        self, user_id: int, guild_id: int, data: UserCustomArs
    ):
        return await self.UserCustomArs.update(
            filter_dict={
                "UserId": user_id,
                "GuildId": guild_id,
            },
            data=data,
        )

    async def GetUserCustomReact(self, user_id: int, guild_id: int) -> UserCustomArs:
        data = await self.UserCustomArs.find(
            {"UserId": user_id, "GuildId": guild_id}
        )
        return data