import discord
from discord.ui import View, Button
from .db import GuildConfig, Backend, ChannelsProfiles, CustomChannelSettings

from utils.views.selects import Channel_select, Select_General
from utils.embed import get_formated_embed, get_formated_field


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

    async def on_error(self, interaction: discord.Interaction, error: Exception):
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


class ChannelProfilesView(View):
    def __init__(
        self,
        interaction: discord.Interaction,
        data: dict[str, ChannelsProfiles],
        settings: CustomChannelSettings,
    ):
        super().__init__(timeout=60)
        self.data = data
        self.settings = settings
        self.user: discord.Member = interaction.user
        self.saved = False

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if interaction.response.is_done():
            return interaction.followup.send(
                "An error occurred: {error}", ephemeral=True
            )
        return interaction.response.send_message(
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

        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Category Name'], data=data['CategoryName'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Top Category Name'], data=data['TopCategoryName'], type='str')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Channel Per Category'], data=data['ChannelPerCategory'], type='int')}\n"
        embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Total Categories'], data=len(data['TotalCategories']), type='int')}\n"
        return embed


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

    async def on_error(self, interaction: discord.Interaction, error: Exception):
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
                embed.description += f"{await get_formated_field(interaction.guild, name=embed_args['Total Categories'], data=len(self.data['ProfileSettings']['CustomChannels']['CustomCategorys']), type='str')}\n"

                await interaction.delete_original_response()
                await interaction.message.edit(embed=embed, view=view)
                self.stop()

            elif view.select.values[0] == "role_profiles":
                pass
            elif view.select.values[0] == "ar_profiles":
                pass
            elif view.select.values[0] == "highlight_profiles":
                pass
            elif view.select.values[0] == "emoji_profiles":
                pass
        else:
            await interaction.delete_original_response()
