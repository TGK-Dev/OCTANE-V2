import discord
from discord.ext import commands
from discord import app_commands, Interaction

from .db import (
    Backend,
    GuildConfig,
    RolesProfiles,
    UserCustomRoles,
    UserCustomChannels,
    UserConfig,
    ChannelsProfiles,
)

import datetime
from humanfriendly import format_timespan

from .views import PerksConfigPanel, RoleFriendsManage, ChannelFriendsManage
from utils.views.buttons import Confirm


class Perks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Backend(bot=bot, CollectionName="Perks")
        self.bot.perks = self.db

    perk = app_commands.Group(
        name="perk", description="Manage your Private custom perks"
    )
    _perks = app_commands.Group(
        name="perks", description="Manage your server members private custom perks"
    )

    role = app_commands.Group(
        name="role", description="Manage your Private custom roles", parent=perk
    )
    channel = app_commands.Group(
        name="channel", description="Manage your Private custom channels", parent=perk
    )

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            message = "You don't have the required permissions to run this command."
        else:
            message = f"An error occurred: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @staticmethod
    def _ModCheck():
        async def _ModRoleCheck(interaction: Interaction):
            if (
                interaction.user.guild_permissions.administrator
                or interaction.user.id in interaction.client.owner_ids
            ):
                return True
            db: Backend = interaction.client.perks
            config = await db.GetGuildConfig(interaction.guild)
            if not config:
                return False
            if config["ModRole"]:
                user_roles = [role.id for role in interaction.user.roles]
                if set(set(config["ModRole"]) & set(user_roles)):
                    return True
            return False

        return app_commands.check(_ModRoleCheck)

    @staticmethod
    def _AdminCheck():
        async def _AdminRoleCheck(interaction: Interaction):
            if (
                interaction.user.guild_permissions.administrator
                or interaction.user.id in interaction.client.owner_ids
            ):
                return True
            return False

        return commands.check(_AdminRoleCheck)

    @_perks.command(name="setup", description="Setup the perks for the server")
    @_AdminCheck()
    async def _perks_setup(self, interaction: Interaction):
        config = await self.db.GetGuildConfig(interaction.guild)
        embed = await self.db.GetConfigEmbed(interaction.guild)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()

    @role.command(name="create", description="Create your own custom role")
    @app_commands.describe(
        name="Name for your custom role",
        color="Color for your custom role",
        role_icon="Icon for your custom role",
    )
    async def _role_create(
        self,
        interaction: Interaction,
        name: str,
        color: str,
        role_icon: discord.Attachment = None,
    ):
        userInfo: UserCustomRoles = await self.db.GetUserCustomRoles(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if userInfo:
            await interaction.response.send_message(
                "You already have a custom role", ephemeral=True
            )
            return
        else:
            embed = discord.Embed(
                description="Please wait while i run few checks",
                color=interaction.client.default_color,
            )
            await interaction.response.send_message(embed=embed)

        guildConfig: GuildConfig = await self.db.GetGuildConfig(interaction.guild)

        userSettings: UserConfig = await self.db.GetUserSettings(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        userRoles = [str(role.id) for role in interaction.user.roles]

        durations = 0
        shareLimit = 0
        claimed_roles = {}
        roleProfiles: dict[str, RolesProfiles] = guildConfig["Profiles"][
            "RolesProfiles"
        ]

        for role in userRoles:
            if role in roleProfiles.keys():
                if str(role) in userSettings["Claimed"]["Roles"].keys():
                    continue

                if durations != "Permanent":
                    if roleProfiles[role]["Duration"] == "Permanent":
                        durations = "Permanent"
                    else:
                        claimed_roles[str(role)] = {
                            "RoleId": int(role),
                            "ClaimedAt": datetime.datetime.utcnow(),
                        }
                        durations += roleProfiles[role]["Duration"]

                shareLimit += roleProfiles[role]["FriendLimit"]

        if durations == 0:
            embed = discord.Embed(
                description="You currently don't have any role which has access to custom roles\n",
                color=interaction.client.default_color,
            )
            embed.description += "-# it's also possible that you may have already claimed temporary roles\n"
            await interaction.edit_original_response(embed=embed)
            return
        else:
            embed = discord.Embed(
                description="All Check Passed | ",
                color=interaction.client.default_color,
            )
            if durations == "Permanent":
                embed.description += "**Duration:** Permanent | Info About Role\n"
            else:
                embed.description += f"**Duration:** {format_timespan(durations)} | "
            embed.description += f"**Share Limit:** {shareLimit} Friends\n\n"

            embed.description += "-# Please wait while i create role you requested"

            await interaction.edit_original_response(embed=embed)

        if durations != "Permanent":
            for role in claimed_roles.keys():
                userSettings["Claimed"]["Roles"][str(role)] = claimed_roles[role]
            await self.db.UpdateUserSettings(
                user_id=interaction.user.id,
                data=userSettings,
                guild_id=interaction.guild.id,
            )

        userRolePorfile: UserCustomRoles = {
            "RoleId": None,
            "GuildId": interaction.guild.id,
            "UserId": interaction.user.id,
            "CreatedAt": None,
            "Duration": durations,
            "Freezed": False,
            "FriendLimit": shareLimit,
            "Friends": [],
            "LastActivity": None,
        }

        role = await self.db.CreateCustomRole(
            name=name,
            color=color,
            guild=interaction.guild,
            config=guildConfig,
            role_icon=role_icon,
            interaction=interaction,
            new_role=True,
        )
        if isinstance(role, tuple):
            embed = discord.Embed(
                description=role[1], color=interaction.client.default_color
            )
            await interaction.edit_original_response(embed=embed)
            return
        else:
            userRolePorfile["RoleId"] = role.id
            userRolePorfile["CreatedAt"] = datetime.datetime.utcnow()
            await self.db.CreateUserCustomRole(userRolePorfile)

            embed = discord.Embed(
                description=f"I have successfully created the role {role.mention} you requested",
                color=interaction.client.default_color,
            )
            await interaction.edit_original_response(embed=embed)
            await interaction.user.add_roles(role)

    @role.command(name="delete", description="Delete your own custom role")
    async def _role_delete(self, interaction: Interaction):
        userInfo: UserCustomRoles = await self.db.GetUserCustomRoles(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not userInfo:
            await interaction.response.send_message(
                "You don't have any custom role", ephemeral=True
            )
            return

        role = interaction.guild.get_role(userInfo["RoleId"])
        if not role:
            await interaction.response.send_message("Role not found", ephemeral=True)
            await self.db.DeleteUserCustomRole(
                user_id=interaction.user.id, guild_id=interaction.guild.id
            )
            return

        embed = discord.Embed(
            description="Are you sure you want to delete your custom role?\nIf your role is temporary it you will lose the remaining time and you will not be able to claim it again",
            color=interaction.client.default_color,
        )
        view = Confirm(user=interaction.user, timeout=30)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            embed = discord.Embed(
                description="Please wait while i delete your role",
                color=interaction.client.default_color,
            )
            await view.interaction.response.edit_message(embed=embed, view=None)
            await role.delete()
            await self.db.DeleteUserCustomRole(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                role_id=role.id,
            )
            embed = discord.Embed(
                description="I have successfully deleted your custom role",
                color=interaction.client.default_color,
            )
            await view.interaction.edit_original_response(embed=embed)

        else:
            await interaction.delete_original_response()

    @role.command(name="edit", description="Edit your own custom role")
    @app_commands.describe(
        name="New name for your custom role",
        color="New color for your custom role",
        role_icon="New icon for your custom role",
    )
    async def _role_edit(
        self,
        interaction: Interaction,
        name: str = None,
        color: str = None,
        role_icon: discord.Attachment = None,
    ):
        UserConfig: UserCustomRoles = await self.db.GetUserCustomRoles(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not UserConfig:
            await interaction.response.send_message(
                "You don't have any custom role", ephemeral=True
            )
            return

        role = interaction.guild.get_role(UserConfig["RoleId"])
        if not role:
            await interaction.response.send_message("Role not found", ephemeral=True)
            await self.db.DeleteUserCustomRole(
                user_id=interaction.user.id, guild_id=interaction.guild.id
            )
            return

        embed = discord.Embed(
            description="Please wait while i edit your role",
            color=interaction.client.default_color,
        )
        await interaction.response.send_message(embed=embed)

        keywords = {}
        if name:
            keywords["name"] = name
        if color:
            keywords["color"] = color
        if role_icon:
            keywords["role_icon"] = role_icon

        await self.db.ModifyCustomRole(role=role, interaction=interaction, **keywords)
        embed = discord.Embed(
            description=f"I have successfully edited your custom role {role.mention}",
            color=interaction.client.default_color,
        )
        await interaction.edit_original_response(embed=embed)

    @role.command(
        name="friends", description="Manage Sharing your custom roles with friends"
    )
    async def _role_friends(self, interaction: Interaction):
        userInfo: UserCustomRoles = await self.db.GetUserCustomRoles(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not userInfo:
            await interaction.response.send_message(
                "You don't have any custom role", ephemeral=True
            )
            return

        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Role Friends Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += f"`Total Role Friends:` {userInfo['FriendLimit']}\n"
        embed.description += (
            f"* Friends: {','.join([f'<@{user}>' for user in userInfo['Friends']])}\n"
        )

        view = RoleFriendsManage(
            member=interaction.user,
            data=userInfo,
            og_interaction=interaction,
            db=self.db,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

    @channel.command(name="create", description="Create your own custom channel")
    @app_commands.describe(name="Name for your custom channel")
    async def _channel_create(self, interaction: Interaction, name: str):
        userInfo: UserCustomChannels = await self.db.GetUserCustomChannels(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if userInfo:
            await interaction.response.send_message(
                "You already have a custom channel", ephemeral=True
            )
            return
        else:
            embed = discord.Embed(
                description="Please wait while i run few checks",
                color=interaction.client.default_color,
            )
            await interaction.response.send_message(embed=embed)

        guildConfig: GuildConfig = await self.db.GetGuildConfig(interaction.guild)

        userSettings: UserConfig = await self.db.GetUserSettings(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        userRoles = [str(role.id) for role in interaction.user.roles]

        durations = 0
        shareLimit = 0
        top = False

        claimed_channels = {}
        channelProfiles: dict[str, ChannelsProfiles] = guildConfig["Profiles"][
            "ChannelsProfiles"
        ]

        for role in userRoles:
            if role in channelProfiles.keys():
                if str(role) in userSettings["Claimed"]["Channels"].keys():
                    continue

                if durations != "Permanent":
                    if channelProfiles[role]["Duration"] == "Permanent":
                        durations = "Permanent"
                    else:
                        claimed_channels[str(role)] = {
                            "RoleId": int(role),
                            "ClaimedAt": datetime.datetime.utcnow(),
                        }
                        durations += channelProfiles[role]["Duration"]

                shareLimit += channelProfiles[role]["FriendLimit"]
                if channelProfiles[role]["TopPosition"]:
                    top = True

        if durations == 0:
            embed = discord.Embed(
                description="You currently don't have any role which has access to custom channels\n",
                color=interaction.client.default_color,
            )
            embed.description += "-# it's also possible that you may have already claimed temporary channels\n"
            await interaction.edit_original_response(embed=embed)
            return
        else:
            embed = discord.Embed(
                description="All Check Passed\n",
                color=interaction.client.default_color,
            )
            if durations == "Permanent":
                embed.description += "**Duration:** Permanent | Info About Channel\n"
            else:
                embed.description += f"**Duration:** {format_timespan(durations)} | "
            embed.description += f"**Share Limit:** {shareLimit} Friends\n\n"

            embed.description += "-# Please wait while i create channel you requested"

            await interaction.edit_original_response(embed=embed)

        if durations != "Permanent":
            for role in claimed_channels.keys():
                userSettings["Claimed"]["Channels"][str(role)] = claimed_channels[role]
            await self.db.UpdateUserSettings(
                user_id=interaction.user.id,
                data=userSettings,
                guild_id=interaction.guild.id,
            )

        userChannelPorfile: UserCustomChannels = {
            "ChannelId": None,
            "GuildId": interaction.guild.id,
            "UserId": interaction.user.id,
            "CreatedAt": None,
            "Duration": durations,
            "Freezed": False,
            "FriendLimit": shareLimit,
            "Friends": [],
            "LastActivity": None,
        }

        channel = await self.db.CreateCustomChannel(
            name=name,
            guild=interaction.guild,
            config=guildConfig,
            interaction=interaction,
            top_cat=top,
        )

        if isinstance(channel, tuple):
            embed = discord.Embed(
                description=channel[1], color=interaction.client.default_color
            )
            await interaction.edit_original_response(embed=embed)
            return

        else:
            userChannelPorfile["ChannelId"] = channel.id
            userChannelPorfile["CreatedAt"] = datetime.datetime.utcnow()
            await self.db.CreateUserCustomChannel(userChannelPorfile)

            embed = discord.Embed(
                description=f"I have successfully created the channel {channel.mention} you requested",
                color=interaction.client.default_color,
            )

            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Jump to Channel",
                    emoji="<:tgk_link:1105189183523401828>",
                    url=f"https://discord.com/channels/{interaction.guild.id}/{channel.id}",
                )
            )

            await interaction.edit_original_response(embed=embed, view=view)

            embed = discord.Embed(
                description="",
                color=interaction.client.default_color,
            )
            if durations == "Permanent":
                embed.description += "**Duration:** Permanent\n"
            else:
                embed.description += f"**Duration:** {format_timespan(durations)}\n"
            embed.description += f"**Share Limit:** {shareLimit} Friends\n\n"

            await channel.send(
                embed=embed,
                content=f"Hey {interaction.user.mention}, Welcome to your custom channel also sorry for stealing first message in this channel",
            )

    @channel.command(name="delete", description="Delete your own custom channel")
    async def _channel_delete(self, interaction: Interaction):
        userInfo: UserCustomChannels = await self.db.GetUserCustomChannels(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not userInfo:
            await interaction.response.send_message(
                "You don't have any custom channel", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(userInfo["ChannelId"])
        if not channel:
            await interaction.response.send_message("Channel not found", ephemeral=True)
            await self.db.DeleteUserCustomChannel(
                user_id=interaction.user.id, guild_id=interaction.guild.id
            )
            return

        embed = discord.Embed(
            description="Are you sure you want to delete your custom channel?\nIf your channel is temporary it you will lose the remaining time and you will not be able to claim it again",
            color=interaction.client.default_color,
        )
        view = Confirm(user=interaction.user, timeout=30)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            embed = discord.Embed(
                description="Please wait while i delete your channel",
                color=interaction.client.default_color,
            )
            await view.interaction.response.edit_message(embed=embed, view=None)
            await channel.delete()
            await self.db.DeleteUserCustomChannel(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                channel_id=channel.id,
            )
            embed = discord.Embed(
                description="I have successfully deleted your custom channel",
                color=interaction.client.default_color,
            )
            await view.interaction.edit_original_response(embed=embed)

        else:
            await interaction.delete_original_response()

    @channel.command(name="edit", description="Edit your own custom channel")
    @app_commands.describe(name="New name for your custom channel")
    async def _channel_edit(self, interaction: Interaction, name: str):
        userInfo: UserCustomChannels = await self.db.GetUserCustomChannels(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not userInfo:
            await interaction.response.send_message(
                "You don't have any custom channel", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(userInfo["ChannelId"])
        if not channel:
            await interaction.response.send_message("Channel not found", ephemeral=True)
            await self.db.DeleteUserCustomChannel(
                user_id=interaction.user.id, guild_id=interaction.guild.id
            )
            return

        embed = discord.Embed(
            description="Please wait while i edit your channel",
            color=interaction.client.default_color,
        )
        await interaction.response.send_message(embed=embed)

        await channel.edit(name=name)

        embed = discord.Embed(
            description=f"I have successfully edited your custom channel {channel.mention}",
            color=interaction.client.default_color,
        )
        await interaction.edit_original_response(embed=embed)

    @channel.command(
        name="friends", description="Manage Sharing your custom channels with friends"
    )
    async def _channel_friends(self, interaction: Interaction):
        userInfo: UserCustomChannels = await self.db.GetUserCustomChannels(
            user_id=interaction.user.id, guild_id=interaction.guild.id
        )
        if not userInfo:
            await interaction.response.send_message(
                "You don't have any custom channel", ephemeral=True
            )
            return

        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Channel Friends Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += f"`Total Channel Friends:` {userInfo['FriendLimit']}\n"
        embed.description += (
            f"* Friends: {','.join([f'<@{user}>' for user in userInfo['Friends']])}\n"
        )

        view = ChannelFriendsManage(
            member=interaction.user,
            data=userInfo,
            og_interaction=interaction,
            db=self.db,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Perks(bot))
