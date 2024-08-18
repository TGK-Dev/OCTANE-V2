import discord
import asyncio
import humanfriendly
from discord.ui import View, Button
from .db import (
    GuildConfig,
    Backend,
    ChannelsProfiles,
    CustomChannelSettings,
    RolesProfiles,
    CustomRoleSettings,
    ArsProfiles,
    HighLightsProfiles,
    EmojisProfiles,
    CustomEmojiSettings,
)

from utils.views.selects import Channel_select, Select_General
from utils.views.modal import General_Modal
from utils.embed import get_formated_embed, get_formated_field
from utils.transformer import TimeConverter
from utils.converters import chunk
from utils.paginator import Paginator

OPTIONS = [
    discord.SelectOption(
        label="Add Profile",
        value="add_profile",
        description="Add a new role profile",
        emoji="<:tgk_add:1073902485959352362>",
    ),
    discord.SelectOption(
        label="Delete Profile",
        value="delete_profile",
        description="Delete a role profile",
        emoji="<:tgk_delete:1113517803203461222>",
    ),
    discord.SelectOption(
        label="Modify Profile",
        value="edit_profile",
        description="Edit a role profile",
        emoji="<:tgk_edit:1073902428224757850>",
    ),
    discord.SelectOption(
        label="View Profiles",
        value="view_profile",
        description="View all role profiles",
        emoji="<:tgk_logging:1107652646887759973>",
    ),
]


class StaffRolesView(View):
    def __init__(self, interaction: discord.Interaction, data: dict):
        super().__init__(timeout=30)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if self.data["AdminRoles"] != []:
            admin_select: discord.ui.RoleSelect = self.children[0]
            admin_select.default_values = [
                discord.SelectDefaultValue(
                    id=role.id, type=discord.SelectDefaultValueType.role
                )
                for role in self.data["AdminRoles"]
            ]
        if self.data["ModRoles"] != []:
            mod_select: discord.ui.RoleSelect = self.children[1]
            mod_select.default_values = [
                discord.SelectDefaultValue(
                    id=role.id, type=discord.SelectDefaultValueType.role
                )
                for role in self.data["ModRoles"]
            ]

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(self, interaction: discord.Interaction, data: dict):
        embed = discord.Embed(
            description="Staff Roles Configuration",
            color=interaction.client.default_color,
        )
        embed.description += f"\n\n**Admin Roles**\n{', '.join([f'{role.mention}' for role in data['AdminRoles']])}"
        embed.description += f"\n\n**Mod Roles**\n{', '.join([f'{role.mention}' for role in data['ModRoles']])}"
        return embed

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Select a Admin Role",
        min_values=1,
        max_values=10,
    )
    async def _admin_roles(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["AdminRoles"] = select.values

        self.children[-1].disabled = False
        select.default_values = [
            discord.SelectDefaultValue(
                id=role.id, type=discord.SelectDefaultValueType.role
            )
            for role in self.data["AdminRoles"]
        ]
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Select a Mod Role",
        min_values=1,
        max_values=10,
    )
    async def _mod_roles(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["ModRoles"] = select.values

        self.children[-1].disabled = False
        select.default_values = [
            discord.SelectDefaultValue(
                id=role.id, type=discord.SelectDefaultValueType.role
            )
            for role in self.data["ModRoles"]
        ]
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        self.data["AdminRoles"] = [int(role.id) for role in self.data["AdminRoles"]]
        self.data["ModRoles"] = [int(role.id) for role in self.data["ModRoles"]]
        button.style = discord.ButtonStyle.green

        for btn in self.children:
            btn.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.saved = True
        self.stop()
        await self._interaction.delete_original_response()


class ChannelProfileModify(View):
    def __init__(self, interaction: discord.Interaction, data: ChannelsProfiles):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if isinstance(self.data["RoleId"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.data["RoleId"], type=discord.SelectDefaultValueType.role
                )
            ]
            self.children[0].disabled = True
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: ChannelsProfiles
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Channel Profile Modification`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            ["Role", "Duration", "Friend Limit", "Top Position"],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=data['FriendLimit'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"
        embed.description += f"{embed_args['Top Position']} {'<:tgk_active:1082676793342951475>' if data['TopPosition'] else '<:tgk_deactivated:1082676877468119110>'}\n"

        return embed

    @discord.ui.select(
        placeholder="Role required to access this profile",
        row=0,
        cls=discord.ui.RoleSelect,
    )
    async def _role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["RoleId"] = select.values[0].id
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.select(
        placeholder="Select a friend limit",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)
        ],
        row=1,
    )
    async def _friend_limit(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.data["FriendLimit"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Duration",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1198684272446414928>",
    )
    async def _duration(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Duration", interaction=interaction)
        view.add_input(
            label="Duration",
            placeholder="Enter the duration for the profile",
            required=True,
            max_length=50,
            default=self.data["Duration"] if self.data["Duration"] else None,
        )

        if self.data["Duration"] == "Permanent":
            view.children[0].default = "Permanent"
        elif isinstance(self.data["Duration"], int):
            view.children[0].default = humanfriendly.format_timespan(
                self.data["Duration"]
            )

        await interaction.response.send_modal(view)
        await view.wait()
        if view.value:
            value = view.children[0].value
            if value.startswith("perm"):
                self.data["Duration"] = "Permanent"
            else:
                value = await TimeConverter().transform(
                    interaction=interaction, argument=value
                )
                if isinstance(value, str):
                    return await view.interaction.response.send_message(
                        content=f"Invald time format: {value}", ephemeral=True
                    )
                self.data["Duration"] = int(value)

            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )

            self.children[-1].disabled = False
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Top Position",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_top:1198684272446414928>",
    )
    async def _top_position(self, interaction: discord.Interaction, button: Button):
        self.data["TopPosition"] = not self.data["TopPosition"]
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        if self.data["Duration"] is None or self.data["RoleId"] is None:
            await interaction.response.send_message(
                content="Duration and Role are required fields", ephemeral=True
            )
        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.saved = True
        self.stop()
        await self._interaction.delete_original_response()


class ChannelProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        data: dict[str, ChannelsProfiles],
        settings: CustomChannelSettings,
        db: Backend,
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.settings = settings
        self.user: discord.Member = interaction.user
        self.saved = False
        self.db = db
        self.message = message

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return await interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return await interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: dict[str, ChannelsProfiles]
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Channel Profiles Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            [
                "Category Name",
                "Top Category Name",
                "Channel Per Category",
                "Total Categories",
            ],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Category Name'], data=self.settings['CategoryName'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Top Category Name'], data=self.settings['TopCategoryName'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Channel Per Category'], data=self.settings['ChannelPerCategory'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Total Categories'], data=len(self.settings['CustomCategorys']), type='str')}\n\n"

        embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made any\n"
        return embed

    @discord.ui.button(
        label="Category Names",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_cc:1150394902585290854>",
    )
    async def _category_name(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Category Naming", interaction=interaction)
        view.add_input(
            label="Category Name",
            placeholder="Channels Per Category",
            required=True,
            max_length=50,
            default=self.settings["CategoryName"]
            if self.settings["CategoryName"]
            else None,
        )
        view.add_input(
            label="Top Category Name",
            placeholder="Enter name you want to use for top category",
            required=True,
            max_length=50,
            default=self.settings["TopCategoryName"]
            if self.settings["TopCategoryName"]
            else None,
        )
        await interaction.response.send_modal(view)

        await view.wait()
        if view.value:
            self.settings["CategoryName"] = view.children[0].value
            self.settings["TopCategoryName"] = view.children[1].value
            self.children[-1].disabled = False
            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )
        else:
            await interaction.delete_original_response()

    @discord.ui.select(
        placeholder="Select number of channels you want for each category",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)
        ],
        row=0,
    )
    async def _category_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.settings["ChannelPerCategory"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Manage Profiles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_create:1107262030399930428>",
    )
    async def _modify_profiles(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Select_General(
            interaction=interaction,
            options=OPTIONS,
            min_values=1,
            max_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if view.value:
            if view.select.values[0] == "add_profile":
                profile_data: ChannelsProfiles = {
                    "Duration": None,
                    "FriendLimit": 0,
                    "RoleId": None,
                    "TopPosition": False,
                }
                create_view = ChannelProfileModify(
                    interaction=interaction, data=profile_data
                )
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Channel Profile Modification`\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    ["Role", "Duration", "Friend Limit", "Top Position"],
                    custom_end=":",
                )
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=profile_data['FriendLimit'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"
                embed.description += f"{embed_args['Top Position']} {'<:tgk_active:1082676793342951475>' if profile_data['TopPosition'] else '<:tgk_deactivated:1082676877468119110>'}\n"

                await view.select.interaction.response.edit_message(
                    embed=embed, view=create_view
                )
                await create_view.wait()
                if create_view.saved:
                    self.data[str(profile_data["RoleId"])] = profile_data
                    self.children[-1].disabled = False
                    await self.message.edit(
                        embed=await self.update_embed(interaction, self.data), view=self
                    )

            elif view.select.values[0] == "delete_profile":
                if self.data == {}:
                    return await view.select.interaction.response.edit_message(
                        content="No profiles to delete",
                        view=None,
                    )
                delete_view = View()
                delete_view.value = None
                options = []
                for profile in self.data.keys():
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        description = ""
                        if isinstance(self.data[profile]["Duration"], int):
                            description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                        else:
                            description += (
                                f"Duration: {self.data[profile]['Duration']} | "
                            )
                        description += (
                            f"Friend Limit: {self.data[profile]['FriendLimit']} | "
                        )
                        description += f"Top Position: {'Yes' if self.data[profile]['TopPosition'] else 'No'}"

                        options.append(
                            discord.SelectOption(
                                label=role.name,
                                value=role.id,
                                description=description,
                            )
                        )
                    else:
                        del self.data[profile]
                delete_view.select = Select_General(
                    interaction=interaction,
                    options=options,
                    min_values=1,
                    max_values=len(options) - 1 if len(options) > 1 else 1,
                )
                delete_view.add_item(delete_view.select)

                await view.select.interaction.response.edit_message(view=delete_view)
                await delete_view.wait()
                if delete_view.value:
                    for value in delete_view.select.values:
                        del self.data[value]
                    self.children[-1].disabled = False
                    await delete_view.select.interaction.response.edit_message(
                        content="Successfully deleted the selected profiles", view=None
                    )

            elif view.select.values[0] == "edit_profile":
                profile_select_view = View()
                profile_select_view.value = None
                options = []
                for profile in self.data.keys():
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        description = ""
                        if isinstance(self.data[profile]["Duration"], int):
                            description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                        else:
                            description += (
                                f"Duration: {self.data[profile]['Duration']} | "
                            )
                        description += (
                            f"Friend Limit: {self.data[profile]['FriendLimit']} | "
                        )
                        description += f"Top Position: {'Yes' if self.data[profile]['TopPosition'] else 'No'}"

                        options.append(
                            discord.SelectOption(
                                label=role.name,
                                value=role.id,
                                description=description,
                            )
                        )
                    else:
                        del self.data[profile]

                profile_select_view.select = Select_General(
                    interaction=interaction,
                    options=options,
                    min_values=1,
                    max_values=1,
                )
                profile_select_view.add_item(profile_select_view.select)

                await view.select.interaction.response.edit_message(
                    view=profile_select_view
                )
                await profile_select_view.wait()
                if profile_select_view.value:
                    try:
                        profile_data = self.data[profile_select_view.select.values[0]]
                    except KeyError:
                        return await profile_select_view.select.interaction.response.edit_message(
                            content="Profile not found", view=None
                        )
                    edit_view = ChannelProfileModify(
                        interaction=interaction, data=profile_data
                    )
                    embed = discord.Embed(
                        description="<:tgk_bank:1134892342910914602> `Channel Profile Modification`\n",
                        color=interaction.client.default_color,
                    )
                    embed_args = await get_formated_embed(
                        ["Role", "Duration", "Friend Limit", "Top Position"],
                        custom_end=":",
                    )
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=profile_data['FriendLimit'], type='str')}\n"
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"
                    embed.description += f"{embed_args['Top Position']} {'<:tgk_active:1082676793342951475>' if profile_data['TopPosition'] else '<:tgk_deactivated:1082676877468119110>'}\n"

                    await profile_select_view.select.interaction.response.edit_message(
                        embed=embed, view=edit_view
                    )
                    await edit_view.wait()
                    if edit_view.saved:
                        self.data[str(profile_data["RoleId"])] = profile_data
                        self.children[-1].disabled = False
                        await self.message.edit(
                            embed=await self.update_embed(interaction, self.data),
                            view=self,
                        )

            elif view.select.values[0] == "view_profile":
                chunked = chunk(self.data.keys(), 2)
                embeds = []
                for chunked_data in chunked:
                    embed = discord.Embed(
                        color=interaction.client.default_color, description=""
                    )
                    for profile in chunked_data:
                        role = interaction.guild.get_role(int(profile))
                        if role:
                            value = f"**Profile Role: {role.mention}**\n"
                            if isinstance(self.data[profile]["Duration"], int):
                                value += f"* Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])}\n"
                            else:
                                value += (
                                    f"* Duration: {self.data[profile]['Duration']}\n"
                                )
                            value += (
                                f"* Friend Limit: {self.data[profile]['FriendLimit']}\n"
                            )
                            value += f"* Top Position: {'Yes' if self.data[profile]['TopPosition'] else 'No'}\n\n"
                            embed.description += value
                        else:
                            del self.data[profile]
                    embeds.append(embed)

                await Paginator(
                    interaction=view.select.interaction, pages=embeds
                ).start(embeded=True, timeout=20, quick_navigation=False, hidden=True)

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        config = await self.db.GetGuildConfig(interaction.guild)
        config["ProfileSettings"]["CustomChannels"] = self.settings
        config["Profiles"]["ChannelsProfiles"] = self.data
        await self.db.UpdateGuildConfig(interaction.guild, config)

        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()

        await interaction.response.edit_message(embed=embed, view=self)

        await asyncio.sleep(2)
        view = PerksConfigPanel(member=self.user, data=config, backend=self.db)
        view.message = interaction.message

        embed = await view.update_embed(interaction, config)
        await interaction.edit_original_response(embed=embed, view=view)


# NOTE: Role Profiles


class RoleProfileModify(View):
    def __init__(self, interaction: discord.Interaction, data: RolesProfiles):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if isinstance(self.data["RoleId"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.data["RoleId"], type=discord.SelectDefaultValueType.role
                )
            ]
            self.children[0].disabled = True
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(self, interaction: discord.Interaction, data: RolesProfiles):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Role Profile Modification`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            ["Role", "Duration", "Friend Limit"],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=data['FriendLimit'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

        return embed

    @discord.ui.select(
        placeholder="Role required to access this profile",
        row=0,
        cls=discord.ui.RoleSelect,
    )
    async def _role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["RoleId"] = select.values[0].id
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.select(
        placeholder="Select a friend limit",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)
        ],
        row=1,
    )
    async def _friend_limit(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.data["FriendLimit"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Duration",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1198684272446414928>",
    )
    async def _duration(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Duration", interaction=interaction)
        view.add_input(
            label="Duration",
            placeholder="Enter the duration for the profile",
            required=True,
            max_length=50,
            default=self.data["Duration"] if self.data["Duration"] else None,
        )

        if self.data["Duration"] == "Permanent":
            view.children[0].default = "Permanent"
        elif isinstance(self.data["Duration"], int):
            view.children[0].default = humanfriendly.format_timespan(
                self.data["Duration"]
            )

        await interaction.response.send_modal(view)
        await view.wait()
        if view.value:
            value = view.children[0].value
            if value.startswith("perm"):
                self.data["Duration"] = "Permanent"
            else:
                value = await TimeConverter().transform(
                    interaction=interaction, argument=value
                )
                if isinstance(value, str):
                    return await view.interaction.response.send_message(
                        content=f"Invald time format: {value}", ephemeral=True
                    )
                self.data["Duration"] = int(value)

            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )

            self.children[-1].disabled = False
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        if self.data["Duration"] is None or self.data["RoleId"] is None:
            await interaction.response.send_message(
                content="Duration and Role are required fields", ephemeral=True
            )
        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.saved = True
        self.stop()
        await self._interaction.delete_original_response()


class RoleProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        db: Backend,
        data: dict[str, RolesProfiles],
        settings: CustomRoleSettings,
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self.settings = settings
        self._interaction = interaction
        self.message = message
        self.db = db

        if isinstance(self.settings["RolePossition"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.settings["RolePossition"],
                    type=discord.SelectDefaultValueType.role,
                )
            ]
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: dict[str, RolesProfiles]
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Role Profiles Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += "`Custom Role Position`:"
        if isinstance(self.settings["RolePossition"], int):
            role = interaction.guild.get_role(self.settings["RolePossition"])
            if role:
                embed.description += f" {role.mention}\n\n"
            else:
                self.settings["RolePossition"] = None
                embed.description += "None\n\n"
        else:
            embed.description += "None\n\n"
        embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"
        return embed

    @discord.ui.select(
        placeholder="select a role for position",
        cls=discord.ui.RoleSelect,
        max_values=1,
    )
    async def _role_position(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.settings["RolePossition"] = int(select.values[0].id)
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Manage Profiles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_entries:1124995375548338176>",
    )
    async def _profiles(self, interaction: discord.Interaction, button: Button):
        self.children[-1].disabled = False
        view = View()
        view.value = None
        view.select = Select_General(
            interaction=interaction,
            options=OPTIONS,
            min_values=1,
            max_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if view.value:
            if view.select.values[0] == "add_profile":
                profile_data: RolesProfiles = {
                    "RoleId": None,
                    "Duration": None,
                    "FriendLimit": 0,
                }
                create_view = RoleProfileModify(
                    interaction=interaction, data=profile_data
                )
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Role Profile Modification`\n\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    ["Duration", "Friend Limit", "Role"],
                    custom_end=":",
                )
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=profile_data['FriendLimit'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"

                await view.select.interaction.response.edit_message(
                    embed=embed, view=create_view
                )
                await create_view.wait()
                if create_view.saved:
                    self.data[str(profile_data["RoleId"])] = profile_data
                    self.children[-1].disabled = False
                    await self.message.edit(
                        embed=await self.update_embed(interaction, self.data), view=self
                    )

            elif view.select.values[0] == "delete_profile":
                if self.data == {}:
                    return await view.select.interaction.response.edit_message(
                        content="No profiles to delete",
                        view=None,
                    )
                delete_view = View()
                delete_view.value = None
                options = []
                for profile in self.data.keys():
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        description = ""
                        if isinstance(self.data[profile]["Duration"], int):
                            description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                        else:
                            description += (
                                f"Duration: {self.data[profile]['Duration']} | "
                            )
                        description += (
                            f"Friend Limit: {self.data[profile]['FriendLimit']} | "
                        )

                        options.append(
                            discord.SelectOption(
                                label=role.name,
                                value=role.id,
                                description=description,
                            )
                        )
                    else:
                        del self.data[profile]
                delete_view.select = Select_General(
                    interaction=interaction,
                    options=options,
                    min_values=1,
                    max_values=len(options) - 1 if len(options) > 1 else 1,
                )
                delete_view.add_item(delete_view.select)

                await view.select.interaction.response.edit_message(view=delete_view)
                await delete_view.wait()
                if delete_view.value:
                    for value in delete_view.select.values:
                        del self.data[value]
                    self.children[-1].disabled = False
                    await delete_view.select.interaction.response.edit_message(
                        content="Successfully deleted the selected profiles", view=None
                    )

            elif view.select.values[0] == "edit_profile":
                profile_select_view = View()
                profile_select_view.value = None
                options = []
                for profile in self.data.keys():
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        description = ""
                        if isinstance(self.data[profile]["Duration"], int):
                            description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                        else:
                            description += (
                                f"Duration: {self.data[profile]['Duration']} | "
                            )
                        description += (
                            f"Friend Limit: {self.data[profile]['FriendLimit']} | "
                        )

                        options.append(
                            discord.SelectOption(
                                label=role.name,
                                value=role.id,
                                description=description,
                            )
                        )
                    else:
                        del self.data[profile]

                profile_select_view.select = Select_General(
                    interaction=interaction,
                    options=options,
                    min_values=1,
                    max_values=1,
                )
                profile_select_view.add_item(profile_select_view.select)

                await view.select.interaction.response.edit_message(
                    view=profile_select_view
                )
                await profile_select_view.wait()
                if profile_select_view.value:
                    try:
                        profile_data = self.data[profile_select_view.select.values[0]]
                    except KeyError:
                        return await profile_select_view.select.interaction.response.edit_message(
                            content="Profile not found", view=None
                        )
                    edit_view = RoleProfileModify(
                        interaction=interaction, data=profile_data
                    )
                    embed = discord.Embed(
                        description="<:tgk_bank:1134892342910914602> `Role Profile Modification`\n",
                        color=interaction.client.default_color,
                    )
                    embed_args = await get_formated_embed(
                        ["Duration", "Friend Limit", "Top Position", "Role"],
                        custom_end=":",
                    )
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Friend Limit'], data=profile_data['FriendLimit'], type='str')}\n"
                    embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"

                    await profile_select_view.select.interaction.response.edit_message(
                        embed=embed, view=edit_view
                    )
                    await edit_view.wait()
                    if edit_view.saved:
                        self.data[str(profile_data["RoleId"])] = profile_data
                        self.children[-1].disabled = False
                        await self.message.edit(
                            embed=await self.update_embed(interaction, self.data),
                            view=self,
                        )

            elif view.select.values[0] == "view_profile":
                chunked = chunk(self.data.keys(), 2)
                embeds = []
                for chunked_data in chunked:
                    embed = discord.Embed(
                        color=interaction.client.default_color, description=""
                    )
                    for profile in chunked_data:
                        role = interaction.guild.get_role(int(profile))
                        if role:
                            value = f"**Profile Role: {role.mention}**\n"
                            if isinstance(self.data[profile]["Duration"], int):
                                value += f"* Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])}\n"
                            else:
                                value += (
                                    f"* Duration: {self.data[profile]['Duration']}\n"
                                )
                            value += (
                                f"* Friend Limit: {self.data[profile]['FriendLimit']}\n"
                            )
                            embed.description += value
                        else:
                            del self.data[profile]
                    embeds.append(embed)

                await Paginator(
                    interaction=view.select.interaction, pages=embeds
                ).start(embeded=True, timeout=20, quick_navigation=False, hidden=True)

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        config = await self.db.GetGuildConfig(interaction.guild)
        config["ProfileSettings"]["CustomRoles"] = self.settings
        config["Profiles"]["RolesProfiles"] = self.data
        await self.db.UpdateGuildConfig(interaction.guild, config)
        for btn in self.children:
            btn.disabled = True
        button.style = discord.ButtonStyle.green
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.saved = True
        self.stop()
        await asyncio.sleep(2)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        view.message = interaction.message
        embed = await view.update_embed(interaction, data=config)
        await interaction.edit_original_response(embed=embed, view=view)


# NOTE: Ar Profiles Views


class ArprofileModify(View):
    def __init__(self, interaction: discord.Interaction, data: ArsProfiles):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if isinstance(self.data["RoleId"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.data["RoleId"], type=discord.SelectDefaultValueType.role
                )
            ]
            self.children[0].disabled = True
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(self, interaction: discord.Interaction, data: ArsProfiles):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `AR Profile Modification`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            ["Role", "Duration", "Trigger Limit"],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=data['TriggerLimit'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

        return embed

    @discord.ui.select(
        placeholder="Role required to access this profile",
        row=0,
        cls=discord.ui.RoleSelect,
    )
    async def _role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["RoleId"] = select.values[0].id
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.select(
        placeholder="Auto React limit",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)
        ],
        row=1,
    )
    async def _trigger_limit(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.data["TriggerLimit"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Duration",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1198684272446414928>",
    )
    async def _duration(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Duration", interaction=interaction)
        view.add_input(
            label="Duration",
            placeholder="Enter the duration for the profile",
            required=True,
            max_length=50,
            default=self.data["Duration"] if self.data["Duration"] else None,
        )

        if self.data["Duration"] == "Permanent":
            view.children[0].default = "Permanent"
        elif isinstance(self.data["Duration"], int):
            view.children[0].default = humanfriendly.format_timespan(
                self.data["Duration"]
            )

        await interaction.response.send_modal(view)
        await view.wait()
        if view.value:
            value = view.children[0].value
            if value.startswith("perm"):
                self.data["Duration"] = "Permanent"
            else:
                value = await TimeConverter().transform(
                    interaction=interaction, argument=value
                )
                if isinstance(value, str):
                    return await view.interaction.response.send_message(
                        content=f"Invald time format: {value}", ephemeral=True
                    )
                self.data["Duration"] = int(value)

            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )

            self.children[-1].disabled = False
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        if self.data["Duration"] is None or self.data["RoleId"] is None:
            await interaction.response.send_message(
                content="Duration and Role are required fields", ephemeral=True
            )
        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.saved = True
        self.stop()
        await self._interaction.delete_original_response()


class ArProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        db: Backend,
        data: dict[str, ArsProfiles],
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        self.db = db
        self.message = message

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: dict[str, ArsProfiles]
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `AR Profiles Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += f"`Total Ar Profiles:` {len(data)}\n\n"
        embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"
        return embed

    @discord.ui.select(
        placeholder="Manage AR Profiles",
        cls=discord.ui.Select,
        options=OPTIONS,
        min_values=1,
        max_values=1,
    )
    async def _profiles(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        if select.values[0] == "add_profile":
            data: ArsProfiles = {
                "Duration": None,
                "RoleId": None,
                "TriggerLimit": 1,
            }
            create_view = ArprofileModify(interaction=interaction, data=data)
            embed = discord.Embed(
                description="<:tgk_bank:1134892342910914602> `AR Profile Modification`\n\n",
                color=interaction.client.default_color,
            )
            embed_args = await get_formated_embed(
                ["Role", "Duration", "Trigger Limit"],
                custom_end=":",
            )
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=data['TriggerLimit'], type='str')}\n"
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

            await interaction.response.send_message(
                embed=embed, view=create_view, ephemeral=True
            )
            await create_view.wait()
            if create_view.saved:
                self.data[str(data["RoleId"])] = data
                self.children[-1].disabled = False
                await self.message.edit(
                    embed=await self.update_embed(interaction, self.data), view=self
                )

        elif select.values[0] == "delete_profile":
            if self.data == {}:
                return await interaction.response.send_message(
                    content="No profiles to delete",
                    view=None,
                )
            delete_view = View()
            delete_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "
                    description += (
                        f"Trigger Limit: {self.data[profile]['TriggerLimit']} | "
                    )

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data
            delete_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=len(options) - 1 if len(options) > 1 else 1,
            )
            delete_view.add_item(delete_view.select)

            await interaction.response.send_message(view=delete_view, ephemeral=True)
            await delete_view.wait()

            if delete_view.value:
                for value in delete_view.select.values:
                    del self.data[value]
                self.children[-1].disabled = False
                await delete_view.select.interaction.response.edit_message(
                    content="Successfully deleted the selected profiles",
                    view=None,
                )

            await interaction.delete_original_response()

        elif select.values[0] == "edit_profile":
            profile_select_view = View()
            profile_select_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "
                    description += (
                        f"Trigger Limit: {self.data[profile]['TriggerLimit']} | "
                    )

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data[profile]

            profile_select_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=1,
            )
            profile_select_view.add_item(profile_select_view.select)

            await interaction.response.send_message(
                view=profile_select_view, ephemeral=True
            )
            await profile_select_view.wait()
            if profile_select_view.value:
                try:
                    profile_data = self.data[profile_select_view.select.values[0]]
                except KeyError:
                    return await profile_select_view.select.interaction.response.edit_message(
                        content="Profile not found", view=None
                    )
                edit_view = ArprofileModify(interaction=interaction, data=profile_data)
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `AR Profile Modification`\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    ["Role", "Duration", "Trigger Limit"],
                    custom_end=":",
                )
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=profile_data['TriggerLimit'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"

                await profile_select_view.select.interaction.response.edit_message(
                    embed=embed, view=edit_view
                )
                await edit_view.wait()

                if edit_view.saved:
                    self.data[str(profile_data["RoleId"])] = profile_data
                    self.children[-1].disabled = False
                    await self.message.edit(
                        embed=await self.update_embed(interaction, self.data), view=self
                    )

        elif select.values[0] == "view_profile":
            chunked = chunk(self.data.keys(), 2)
            embeds = []
            for chunked_data in chunked:
                embed = discord.Embed(
                    color=interaction.client.default_color, description=""
                )
                for profile in chunked_data:
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        value = f"**Profile Role: {role.mention}**\n"
                        if isinstance(self.data[profile]["Duration"], int):
                            value += f"* Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])}\n"
                        else:
                            value += f"* Duration: {self.data[profile]['Duration']}\n"
                        value += (
                            f"* Trigger Limit: {self.data[profile]['TriggerLimit']}\n"
                        )
                        embed.description += value
                    else:
                        del self.data[profile]
                embeds.append(embed)

            await Paginator(interaction=interaction, pages=embeds).start(
                embeded=True, timeout=20, quick_navigation=False, hidden=True
            )

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        config = await self.db.GetGuildConfig(interaction.guild)
        config["Profiles"]["ArsProfiles"] = self.data
        await self.db.UpdateGuildConfig(interaction.guild, config)

        for btn in self.children:
            btn.disabled = True
        button.style = discord.ButtonStyle.green

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)

        self.saved = True
        self.stop()
        await asyncio.sleep(2)

        embed = await self.db.GetConfigEmbed(interaction.guild)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        await interaction.edit_original_response(embed=embed, view=view)
        view.message = interaction.message


# NOTE: Hightlight Views


class HighlightModify(View):
    def __init__(self, interaction: discord.Interaction, data: HighLightsProfiles):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if isinstance(self.data["RoleId"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.data["RoleId"], type=discord.SelectDefaultValueType.role
                )
            ]
            self.children[0].disabled = True
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: HighLightsProfiles
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Highlight Profile Modification`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            ["Role", "Duration", "Trigger Limit"],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=data['TriggerLimit'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

        return embed

    @discord.ui.select(
        placeholder="Role required to access this profile",
        row=0,
        cls=discord.ui.RoleSelect,
    )
    async def _role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["RoleId"] = select.values[0].id
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.select(
        placeholder="Highlight limit",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)
        ],
        row=1,
    )
    async def _trigger_limit(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.data["TriggerLimit"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Duration",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1198684272446414928>",
    )
    async def _duration(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Duration", interaction=interaction)
        view.add_input(
            label="Duration",
            placeholder="Enter the duration for the profile",
            required=True,
            max_length=50,
            default=self.data["Duration"] if self.data["Duration"] else None,
        )

        if self.data["Duration"] == "Permanent":
            view.children[0].default = "Permanent"
        elif isinstance(self.data["Duration"], int):
            view.children[0].default = humanfriendly.format_timespan(
                self.data["Duration"]
            )

        await interaction.response.send_modal(view)
        await view.wait()
        if view.value:
            value = view.children[0].value
            if value.startswith("perm"):
                self.data["Duration"] = "Permanent"
            else:
                value = await TimeConverter().transform(
                    interaction=interaction, argument=value
                )
                if isinstance(value, str):
                    return await view.interaction.response.send_message(
                        content=f"Invald time format: {value}", ephemeral=True
                    )
                self.data["Duration"] = int(value)

            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )

            self.children[-1].disabled = False
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        if self.data["Duration"] is None or self.data["RoleId"] is None:
            await interaction.response.send_message(
                content="Duration and Role are required fields", ephemeral=True
            )

        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)

        self.saved = True
        self.stop()
        await self._interaction.delete_original_response()


class HighlightProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        db: Backend,
        data: dict[str, HighLightsProfiles],
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        self.db = db
        self.message = message

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: dict[str, HighLightsProfiles]
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Highlight Profiles Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += f"`Total Highlight Profiles:` {len(data)}\n\n"
        embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"
        return embed

    @discord.ui.select(
        placeholder="Manage Highlight Profiles",
        cls=discord.ui.Select,
        options=OPTIONS,
        min_values=1,
        max_values=1,
    )
    async def _profiles(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        if select.values[0] == "add_profile":
            data: HighLightsProfiles = {
                "Duration": None,
                "RoleId": None,
                "TriggerLimit": 1,
            }
            create_view = HighlightModify(interaction=interaction, data=data)
            embed = discord.Embed(
                description="<:tgk_bank:1134892342910914602> `Highlight Profile Modification`\n\n",
                color=interaction.client.default_color,
            )
            embed_args = await get_formated_embed(
                ["Role", "Duration", "Trigger Limit"],
                custom_end=":",
            )
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=data['TriggerLimit'], type='str')}\n"
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

            await interaction.response.send_message(
                embed=embed, view=create_view, ephemeral=True
            )
            await create_view.wait()
            if create_view.saved:
                self.data[str(data["RoleId"])] = data
                self.children[-1].disabled = False
                await self.message.edit(
                    embed=await self.update_embed(interaction, self.data), view=self
                )

        elif select.values[0] == "delete_profile":
            if self.data == {}:
                return await interaction.response.send_message(
                    content="No profiles to delete",
                    view=None,
                )
            delete_view = View()
            delete_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "
                    description += (
                        f"Trigger Limit: {self.data[profile]['TriggerLimit']} | "
                    )

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data[profile]

            delete_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=len(options) - 1 if len(options) > 1 else 1,
            )
            delete_view.add_item(delete_view.select)

            await interaction.response.send_message(view=delete_view, ephemeral=True)

            await delete_view.wait()
            if delete_view.value:
                for value in delete_view.select.values:
                    del self.data[value]
                self.children[-1].disabled = False
                await delete_view.select.interaction.response.edit_message(
                    content="Successfully deleted the selected profiles",
                    view=None,
                )
                await self.message.edit(
                    embed=await self.update_embed(interaction, self.data), view=self
                )
            await interaction.delete_original_response()

        elif select.values[0] == "edit_profile":
            profile_select_view = View()
            profile_select_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "
                    description += (
                        f"Trigger Limit: {self.data[profile]['TriggerLimit']} | "
                    )

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data[profile]

            profile_select_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=1,
            )
            profile_select_view.add_item(profile_select_view.select)

            await interaction.response.send_message(
                view=profile_select_view, ephemeral=True
            )
            await profile_select_view.wait()
            if profile_select_view.value:
                try:
                    profile_data = self.data[profile_select_view.select.values[0]]
                except KeyError:
                    return await profile_select_view.select.interaction.response.edit_message(
                        content="Profile not found", view=None
                    )
                edit_view = HighlightModify(interaction=interaction, data=profile_data)
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Highlight Profile Modification`\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    ["Role", "Duration", "Trigger Limit"],
                    custom_end=":",
                )
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Trigger Limit'], data=profile_data['TriggerLimit'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"

                await profile_select_view.select.interaction.response.edit_message(
                    embed=embed, view=edit_view
                )
                await edit_view.wait()

                if edit_view.saved:
                    self.data[str(profile_data["RoleId"])] = profile_data
                    self.children[-1].disabled = False
                    await self.message.edit(
                        embed=await self.update_embed(interaction, self.data), view=self
                    )

        elif select.values[0] == "view_profile":
            chunked = chunk(self.data.keys(), 2)
            embeds = []
            for chunked_data in chunked:
                embed = discord.Embed(
                    color=interaction.client.default_color, description=""
                )
                for profile in chunked_data:
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        value = f"**Profile Role: {role.mention}**\n"
                        if isinstance(self.data[profile]["Duration"], int):
                            value += f"* Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])}\n"
                        else:
                            value += f"* Duration: {self.data[profile]['Duration']}\n"
                        value += (
                            f"* Trigger Limit: {self.data[profile]['TriggerLimit']}\n"
                        )
                        embed.description += value
                    else:
                        del self.data[profile]
                embeds.append(embed)

            await Paginator(interaction=interaction, pages=embeds).start(
                embeded=True, timeout=20, quick_navigation=False, hidden=True
            )

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        config = await self.db.GetGuildConfig(interaction.guild)
        config["Profiles"]["HighLightsProfiles"] = self.data
        await self.db.UpdateGuildConfig(interaction.guild, config)

        for btn in self.children:
            btn.disabled = True
        button.style = discord.ButtonStyle.green

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)

        self.saved = True
        self.stop()
        await asyncio.sleep(2)

        embed = await self.db.GetConfigEmbed(interaction.guild)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        await self.message.edit(embed=embed, view=view)
        view.message = interaction.message


# NOTE: Emoji Profiles Views


class EmojiModify(View):
    def __init__(self, interaction: discord.Interaction, data: EmojisProfiles):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        if isinstance(self.data["RoleId"], int):
            self.children[0].default_values = [
                discord.SelectDefaultValue(
                    id=self.data["RoleId"], type=discord.SelectDefaultValueType.role
                )
            ]
            self.children[0].disabled = True
            self.children[-1].disabled = False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: EmojisProfiles
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Emoji Profile Modification`\n\n",
            color=interaction.client.default_color,
        )
        embed_args = await get_formated_embed(
            ["Role", "Duration"],
            custom_end=":",
        )

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

        return embed

    @discord.ui.select(
        placeholder="Role required to access this profile",
        row=0,
        cls=discord.ui.RoleSelect,
    )
    async def _role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        self.data["RoleId"] = select.values[0].id
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Duration",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1198684272446414928>",
    )
    async def _duration(self, interaction: discord.Interaction, button: Button):
        view = General_Modal(title="Duration", interaction=interaction)
        view.add_input(
            label="Duration",
            placeholder="Enter the duration for the profile",
            required=True,
            max_length=50,
            default=self.data["Duration"] if self.data["Duration"] else None,
        )

        if self.data["Duration"] == "Permanent":
            view.children[0].default = "Permanent"
        elif isinstance(self.data["Duration"], int):
            view.children[0].default = humanfriendly.format_timespan(
                self.data["Duration"]
            )

        await interaction.response.send_modal(view)
        await view.wait()
        if view.value:
            value = view.children[0].value
            if value.startswith("perm"):
                self.data["Duration"] = "Permanent"
            else:
                value = await TimeConverter().transform(
                    interaction=interaction, argument=value
                )
                if isinstance(value, str):
                    return await view.interaction.response.send_message(
                        content=f"Invald time format: {value}", ephemeral=True
                    )
                self.data["Duration"] = int(value)

            await view.interaction.response.edit_message(
                embed=await self.update_embed(interaction, self.data), view=self
            )

            self.children[-1].disabled = False
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        if self.data["Duration"] is None or self.data["RoleId"] is None:
            await interaction.response.send_message(
                content="Duration and Role are required fields", ephemeral=True
            )

        button.style = discord.ButtonStyle.green
        for btn in self.children:
            btn.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)

        self.saved = True
        self.stop()


class EmojiProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        db: Backend,
        data: dict[str, EmojisProfiles],
        settings: dict[str, CustomEmojiSettings],
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.saved = False
        self._interaction = interaction
        self.db = db
        self.message = message
        self.settings = settings

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def update_embed(
        self, interaction: discord.Interaction, data: dict[str, EmojisProfiles]
    ):
        embed = discord.Embed(
            description="<:tgk_bank:1134892342910914602> `Emoji Profiles Configuration`\n\n",
            color=interaction.client.default_color,
        )
        embed.description += (
            f"`Max Custom Emoji Limit:` {self.settings['TotalCustomEmojisLimit']}\n"
        )
        embed.description += f"`Total Emoji Profiles  :` {len(data)}\n\n"
        embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"
        return embed

    @discord.ui.select(
        placeholder="Select max custom emoji limit",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 24)
        ],
    )
    async def _max_emoji_limit(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.settings["MaxEmojiLimit"] = int(select.values[0])
        self.children[-1].disabled = False
        await interaction.response.edit_message(
            embed=await self.update_embed(interaction, self.data), view=self
        )

    @discord.ui.button(
        label="Manage Profiles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_entries:1124995375548338176>",
    )
    async def _manage_profile(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Select_General(
            interaction=interaction,
            options=OPTIONS,
            min_values=1,
            max_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.select.values[0] == "add_profile":
            data: EmojisProfiles = {
                "Duration": None,
                "RoleId": None,
            }
            create_view = EmojiModify(interaction=interaction, data=data)
            embed = discord.Embed(
                description="<:tgk_bank:1134892342910914602> `Emoji Profile Modification`\n\n",
                color=interaction.client.default_color,
            )
            embed_args = await get_formated_embed(
                ["Role", "Duration"],
                custom_end=":",
            )
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=data['RoleId'], type='role')}\n"
            embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=data['Duration'], type='time')}\n"

            await view.select.interaction.response.edit_message(
                embed=embed, view=create_view
            )
            await create_view.wait()
            if create_view.saved:
                self.data[str(data["RoleId"])] = data
                self.children[-1].disabled = False
                await self.message.edit(
                    embed=await self.update_embed(interaction, self.data), view=self
                )
            await create_view._interaction.delete_original_response()

        elif view.select.values[0] == "delete_profile":
            if self.data == {}:
                return await interaction.response.send_message(
                    content="No profiles to delete",
                    view=None,
                )
            delete_view = View()
            delete_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data[profile]
            delete_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=len(options) - 1 if len(options) > 1 else 1,
            )
            delete_view.add_item(delete_view.select)

            await view.select.interaction.response.edit_message(view=delete_view)
            await delete_view.wait()
            if delete_view.value:
                for value in delete_view.select.values:
                    del self.data[value]
                self.children[-1].disabled = False
                await delete_view.select.interaction.response.edit_message(
                    content="Successfully deleted the selected profiles",
                    view=None,
                    delete_after=1.5,
                )
                await interaction.edit_original_response(
                    embed=await self.update_embed(interaction, self.data), view=self
                )

        elif view.select.values[0] == "edit_profile":
            profile_select_view = View()
            profile_select_view.value = None
            options = []
            for profile in self.data.keys():
                role = interaction.guild.get_role(int(profile))
                if role:
                    description = ""
                    if isinstance(self.data[profile]["Duration"], int):
                        description += f"Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])} | "
                    else:
                        description += f"Duration: {self.data[profile]['Duration']} | "

                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=role.id,
                            description=description,
                        )
                    )
                else:
                    del self.data[profile]

            profile_select_view.select = Select_General(
                interaction=interaction,
                options=options,
                min_values=1,
                max_values=1,
            )
            profile_select_view.add_item(profile_select_view.select)

            await view.select.interaction.response.edit_message(
                view=profile_select_view
            )
            await profile_select_view.wait()
            if profile_select_view.value:
                try:
                    profile_data = self.data[profile_select_view.select.values[0]]
                except KeyError:
                    return await profile_select_view.select.interaction.response.send_message(
                        content="Profile not found", view=None
                    )
                edit_view = EmojiModify(interaction=interaction, data=profile_data)
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Emoji Profile Modification`\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    ["Duration", "Role"],
                    custom_end=":",
                )
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Role'], data=profile_data['RoleId'], type='role')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Duration'], data=profile_data['Duration'], type='time')}\n"

                await profile_select_view.select.interaction.response.edit_message(
                    embed=embed, view=edit_view
                )
                await edit_view.wait()

                if edit_view.saved:
                    self.data[str(profile_data["RoleId"])] = profile_data
                    self.children[-1].disabled = False
                    embed = await self.update_embed(interaction, self.data)
                    await profile_select_view.select.interaction.edit_original_response(
                        view=self, embed=embed
                    )

        elif view.select.values[0] == "view_profile":
            chunked = chunk(self.data.keys(), 2)
            embeds = []
            for chunked_data in chunked:
                embed = discord.Embed(
                    color=interaction.client.default_color, description=""
                )
                for profile in chunked_data:
                    role = interaction.guild.get_role(int(profile))
                    if role:
                        value = f"**Profile Role: {role.mention}**\n"
                        if isinstance(self.data[profile]["Duration"], int):
                            value += f"* Duration: {humanfriendly.format_timespan(self.data[profile]['Duration'])}\n"
                        else:
                            value += f"* Duration: {self.data[profile]['Duration']}\n"
                        embed.description += value
                    else:
                        del self.data[profile]
                embeds.append(embed)

            await Paginator(interaction=interaction, pages=embeds).start(
                embeded=True, timeout=20, quick_navigation=False, hidden=True
            )
        else:
            await view.select.interaction.response.send_message(
                content="Invalid option selected", view=None, ephemeral=True
            )

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
        row=4,
    )
    async def _save(self, interaction: discord.Interaction, button: Button):
        config = await self.db.GetGuildConfig(interaction.guild)
        config["Profiles"]["EmojisProfiles"] = self.data
        await self.db.UpdateGuildConfig(interaction.guild, config)

        for btn in self.children:
            btn.disabled = True
        button.style = discord.ButtonStyle.green

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)

        self.saved = True
        self.stop()
        await asyncio.sleep(2)

        embed = await self.db.GetConfigEmbed(interaction.guild)
        view = PerksConfigPanel(member=interaction.user, data=config, backend=self.db)
        await self.message.edit(embed=embed, view=view)
        view.message = interaction.message


class PerksConfigPanel(View):
    def __init__(
        self,
        member: discord.Member,
        data: GuildConfig,
        backend: Backend,
        message: discord.Message = None,
    ):
        self.member: discord.Member = member
        self.data: GuildConfig = data
        self.message: discord.Message = message
        self.backend: Backend = backend
        super().__init__(timeout=None)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
            f"An error occurred: {error}", ephemeral=True
        )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.member.id:
            return True
        else:
            await interaction.response.send_message(
                content="You are not allowed to interact with this message.",
                ephemeral=True,
            )
            return False

    async def update_embed(self, interaction: discord.Interaction, data: GuildConfig):
        embed = await self.backend.GetConfigEmbed(interaction.guild)
        return embed

    @discord.ui.button(
        label="Staff Roles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_role:1073908306713780284>",
    )
    async def _admin_roles(self, interaction: discord.Interaction, button: Button):
        data = {
            "AdminRoles": [
                interaction.guild.get_role(role) for role in self.data["AdminRoles"]
            ],
            "ModRoles": [
                interaction.guild.get_role(role) for role in self.data["ModRoles"]
            ],
        }
        view = StaffRolesView(interaction=interaction, data=data)
        embed = discord.Embed(
            description="Staff Roles Configuration",
            color=interaction.client.default_color,
        )
        embed.description += f"\n\n**Admin Roles**\n{', '.join([f'{role.mention}' for role in data['AdminRoles']])}"
        embed.description += f"\n\n**Mod Roles**\n{', '.join([f'{role.mention}' for role in data['ModRoles']])}"
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.saved:
            self.data["AdminRoles"] = view.data["AdminRoles"]
            self.data["ModRoles"] = view.data["ModRoles"]
            await self.backend.UpdateGuildConfig(interaction.guild, self.data)
            await self.update_embed(interaction, self.data)
            await self.message.edit(
                embed=await self.update_embed(interaction, self.data), view=self
            )
        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Log Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_logging:1107652646887759973>",
    )
    async def _log_channel(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Channel_select(
            placeholder="Select a channel where logs will be sent",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
        )

        if self.data["LogChannel"]:
            channel = interaction.guild.get_channel(self.data["LogChannel"])
            if not channel:
                self.data["LogChannel"] = None
            else:
                view.select.default_values = [
                    discord.SelectDefaultValue(
                        id=channel.id, type=discord.SelectDefaultValueType.channel
                    )
                ]

        view.add_item(view.select)

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

        await view.wait()
        if view.value:
            channel: discord.TextChannel = interaction.guild.get_channel(
                view.select.values[0].id
            )
            if not isinstance(channel, discord.TextChannel):
                return await view.select.interaction.response.edit_message(
                    "Make sure you i have access to the channel and it's a text channel",
                    view=None,
                )
            if not any(
                [
                    channel.permissions_for(interaction.guild.me).send_messages,
                    channel.permissions_for(interaction.guild.me).embed_links,
                    channel.permissions_for(interaction.guild.me).read_message_history,
                ]
            ):
                return await view.select.interaction.response.edit_message(
                    f"I don't have the required (send messages, embed links, read message history) permissions in {channel.mention} to send logs.",
                    view=None,
                )
            self.data["LogChannel"] = channel.id
            await self.backend.UpdateGuildConfig(interaction.guild, self.data)
            await self.message.edit(
                embed=await self.update_embed(interaction, self.data), view=self
            )
            await view.select.interaction.response.edit_message(
                content=f"<:tgk_active:1082676793342951475>: Logging channel set to {channel.mention}",
                view=None,
                delete_after=2.5,
            )

        else:
            await interaction.delete_original_response()

    @discord.ui.button(
        label="Profiles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_entries:1124995375548338176>",
    )
    async def _profiles(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Select_General(
            interaction=interaction,
            options=[
                discord.SelectOption(
                    label="Channel Profiles",
                    value="channel_profiles",
                    description="Manage channel profiles",
                    emoji="<:tgk_channel:1073908465405268029>",
                ),
                discord.SelectOption(
                    label="Role Profiles",
                    value="role_profiles",
                    description="Manage role profiles",
                    emoji="<:tgk_role:1073908306713780284>",
                ),
                discord.SelectOption(
                    label="Ar Profiles",
                    value="ar_profiles",
                    description="Manage ar profiles",
                    emoji="<:tgk_color:1107261678204244038>",
                ),
                discord.SelectOption(
                    label="Highlight Profiles",
                    value="highlight_profiles",
                    description="Manage highlight profiles",
                    emoji="<:tgk_message:1113527047373979668>",
                ),
                discord.SelectOption(
                    label="Emoji Profiles",
                    value="emoji_profiles",
                    description="Manage emoji profiles",
                    emoji="<:tgk_fishing:1196665275794325504>",
                ),
            ],
            min_values=1,
            max_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if view.value:
            if view.select.values[0] == "channel_profiles":
                view = ChannelProfilesView(
                    interaction=interaction,
                    data=self.data["Profiles"]["ChannelsProfiles"],
                    settings=self.data["ProfileSettings"]["CustomChannels"],
                    db=self.backend,
                )
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Channel Profiles Configuration`\n\n",
                    color=interaction.client.default_color,
                )
                embed_args = await get_formated_embed(
                    [
                        "Category Name",
                        "Top Category Name",
                        "Channel Per Category",
                        "Total Categories",
                    ],
                    custom_end=":",
                )

                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Category Name'], data=self.data['ProfileSettings']['CustomChannels']['CategoryName'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Top Category Name'], data=self.data['ProfileSettings']['CustomChannels']['TopCategoryName'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Channel Per Category'], data=self.data['ProfileSettings']['CustomChannels']['ChannelPerCategory'], type='str')}\n"
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Total Categories'], data=len(self.data['ProfileSettings']['CustomChannels']['CustomCategorys']), type='str')}\n\n"

                embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made any"

                await interaction.delete_original_response()
                await interaction.message.edit(embed=embed, view=view)
                view.message = interaction.message
                self.stop()

            elif view.select.values[0] == "role_profiles":
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Role Profiles Configuration`\n\n",
                    color=interaction.client.default_color,
                )
                embed.description += "`Custom Role Position`:"
                if isinstance(
                    self.data["ProfileSettings"]["CustomRoles"]["RolePossition"], int
                ):
                    role = interaction.guild.get_role(
                        self.data["ProfileSettings"]["CustomRoles"]["RolePossition"]
                    )
                    if role:
                        embed.description += f" {role.mention}\n"
                    else:
                        self.data["ProfileSettings"]["CustomRoles"]["RolePossition"] = (
                            None
                        )
                        embed.description += "None\n\n"
                else:
                    embed.description += "None\n\n"
                embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"

                role_profile_view = RoleProfilesView(
                    interaction=interaction,
                    db=self.backend,
                    data=self.data["Profiles"]["RolesProfiles"],
                    settings=self.data["ProfileSettings"]["CustomRoles"],
                )
                self.stop()
                await interaction.delete_original_response()
                await self.message.edit(embed=embed, view=role_profile_view)
                role_profile_view.message = self.message

            elif view.select.values[0] == "ar_profiles":
                ar_view = ArProfilesView(
                    interaction=interaction,
                    data=self.data["Profiles"]["ArsProfiles"],
                    db=self.backend,
                )
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `AR Profiles Configuration`\n\n",
                    color=interaction.client.default_color,
                )
                embed.description += f"`Total AR Profiles:` {len(self.data['Profiles']['ArsProfiles'])}\n\n"
                embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"
                await interaction.delete_original_response()
                await self.message.edit(embed=embed, view=ar_view)
                ar_view.message = self.message

            elif view.select.values[0] == "highlight_profiles":
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Highlight Profiles Configuration`\n\n",
                    color=interaction.client.default_color,
                )
                embed.description += f"`Total Highlight Profiles:` {len(self.data['Profiles']['HighLightsProfiles'])}\n\n"
                embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"

                highlight_view = HighlightProfilesView(
                    interaction=interaction,
                    db=self.backend,
                    data=self.data["Profiles"]["HighLightsProfiles"],
                )
                await interaction.delete_original_response()
                await self.message.edit(embed=embed, view=highlight_view)
                highlight_view.message = self.message

            elif view.select.values[0] == "emoji_profiles":
                embed = discord.Embed(
                    description="<:tgk_bank:1134892342910914602> `Emoji Profiles Configuration`\n\n",
                    color=interaction.client.default_color,
                )
                embed.description += f"`Max Custom Emoji Limit:` {self.data['ProfileSettings']['CustomEmoji']['TotalCustomEmojisLimit']}\n"
                embed.description += f"`Total Emoji Profiles  :` {len(self.data['Profiles']['EmojisProfiles'])}\n\n"

                embed.description += "-# <:tgk_hint:1206282482744561744> Make sure to save your changes if made\n-# * Any changes to role position will be only applied new custom roles\n"

                emoji_view = EmojiProfilesView(
                    interaction=interaction,
                    db=self.backend,
                    data=self.data["Profiles"]["EmojisProfiles"],
                    settings=self.data["ProfileSettings"]["CustomEmoji"],
                )
                await interaction.delete_original_response()
                await self.message.edit(embed=embed, view=emoji_view)
                emoji_view.message = self.message

        else:
            await interaction.delete_original_response()
