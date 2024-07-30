import asyncio
import aiohttp
import discord
from discord import Interaction, SelectOption, app_commands
from discord.ui import View, Button, button, TextInput, Item, Select, select
from utils.views.selects import Role_select, Select_General, Channel_select
from utils.views.modal import General_Modal
from utils.embed import get_formated_embed, get_formated_field
from utils.paginator import Paginator
from .db import Config, Profile, Custom_Emoji
import traceback

profile_select_options = [
    SelectOption(label="Roles", value="roles"),
    SelectOption(label="Channels", value="channels"),
    SelectOption(label="Auto Reacts", value="reacts"),
    SelectOption(label="Highlighters", value="highlights"),
    SelectOption(label="Emojis", value="emojis"),
]


class ButtonCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after

    def key(interaction: discord.Interaction):
        return interaction.user


class PerkConfig(View):
    def __init__(
        self, user: discord.Member, data: Config, message: discord.Message = None
    ):
        self.user = user
        self.data = data
        self.message = message
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message(
                "You are not the owner of this perk", ephemeral=True
            )
            return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            await self.message.edit(view=self)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

    @button(
        label="Admin Roles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_admin:1073908306713780284>",
        row=1,
    )
    async def admin_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(
            placeholder="Select a role to add/remove from admin roles",
            max_values=10,
            min_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            add_roles = []
            remove_roles = []
            for value in view.select.values:
                if value.id in self.data["admin_roles"]:
                    self.data["admin_roles"].remove(value.id)
                    remove_roles.append(value)
                else:
                    self.data["admin_roles"].append(value.id)
                    add_roles.append(value)

            await view.select.interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"Added Roles: {', '.join([role.mention for role in add_roles]) if add_roles else '`None`'}\nRemoved Roles: {', '.join([role.mention for role in remove_roles]) if remove_roles else '`None`'}",
                    color=interaction.client.default_color,
                ),
                delete_after=10,
            )

            await interaction.client.Perk.update("config", self.data)
            await self.message.edit(
                embed=await interaction.client.Perk.get_config_embed(
                    interaction.guild, self.data
                )
            )

    @button(
        label="Custom Roles Position",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_role:1073908306713780284>",
        row=1,
    )
    async def custom_roles_position(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(
            placeholder="Select a role to set the position of custom roles",
            max_values=1,
            min_values=1,
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            position = view.select.values[0]
            if (
                position >= interaction.guild.me.top_role
                or position >= interaction.user.top_role
            ):
                return await view.select.interaction.response.send_message(
                    content="You can't set the position of custom roles to a role higher than  or my top role",
                    view=None,
                    ephemeral=True,
                )
            if position == interaction.guild.default_role.position:
                return await view.select.interaction.response.send_message(
                    content="You can't set the position of custom roles to the default role",
                    view=None,
                    ephemeral=True,
                )

            self.data["custom_roles_position"] = position.id
            await interaction.client.Perk.update("config", self.data)
            await view.select.interaction.response.edit_message(
                content=f"Custom roles position set to <@&{position}>", view=None
            )
            await self.message.edit(
                embed=await interaction.client.Perk.get_config_embed(
                    interaction.guild, self.data
                )
            )
            await self.message.edit(
                embed=await self.update_embed(interaction, self.data)
            )

    @button(
        label="Custom Category",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_category:1076602579846447184>",
        row=1,
    )
    async def custom_category(self, interaction: Interaction, button: Button):
        view = General_Modal(title="Custom Category", interaction=interaction)
        view.name = TextInput(
            label="Enter the name of the category",
            min_length=1,
            max_length=100,
            required=True,
        )
        view.top_cat = TextInput(
            label="Enter the name of the top category",
            min_length=1,
            max_length=100,
            required=True,
        )

        if self.data["custom_category"]["name"]:
            view.name.default = self.data["custom_category"]["name"]

        if self.data["top_channel_category"]["name"]:
            view.top_cat.default = self.data["top_channel_category"]["name"]

        view.add_item(view.name)
        view.add_item(view.top_cat)

        await interaction.response.send_modal(view)
        await view.wait()
        if not view.value:
            return

        if self.data["custom_category"]["name"] is None:
            cat = await interaction.guild.create_category_channel(
                name=f"{view.name.value} - 1"
            )
            self.data["custom_category"]["last_cat"] = cat.id
            self.data["custom_category"]["cat_list"].append(cat.id)

        self.data["custom_category"]["name"] = view.name.value

        self.data["top_channel_category"]["name"] = view.top_cat.value

        await interaction.client.Perk.update("config", self.data)
        await view.interaction.response.edit_message(
            embed=await interaction.client.Perk.get_config_embed(
                interaction.guild, self.data
            ),
            view=self,
        )

        top_cat = interaction.guild.get_channel(
            self.data["top_channel_category"]["cat_id"]
        )
        if top_cat:
            await top_cat.edit(name=view.top_cat.value)
        else:
            top_cat = await interaction.guild.create_category_channel(
                name=view.top_cat.value, position=0
            )
            self.data["top_channel_category"]["cat_id"] = top_cat.id
            await interaction.client.Perk.update("config", self.data)

        for cat in self.data["custom_category"]["cat_list"]:
            await asyncio.sleep(0.2)
            cat = interaction.guild.get_channel(cat)
            if cat:
                await cat.edit(
                    name=f"{self.data['custom_category']['name']} - {self.data['custom_category']['cat_list'].index(cat.id) + 1}"
                )

    @button(
        label="Max Emojis",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_emoji:1073908306713780284>",
        row=2,
    )
    async def max_emojis(self, interaction: Interaction, button: Button):
        view = General_Modal(title="Max Emojis", interaction=interaction)
        view.max_emojis = TextInput(
            label="Enter the max emojis", min_length=1, max_length=2, required=True
        )
        if self.data["emojis"]["max"]:
            view.max_emojis.default = str(self.data["emojis"]["max"])

        view.add_item(view.max_emojis)

        await interaction.response.send_modal(view)
        await view.wait()

        if view.max_emojis.value:
            self.data["emojis"]["max"] = int(view.max_emojis.value)
            await interaction.client.Perk.update("config", self.data)
            await view.interaction.response.edit_message(
                embed=await interaction.client.Perk.get_config_embed(
                    interaction.guild, self.data
                ),
                view=self,
            )

    @button(
        label="Emoji Request Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_emoji:1073908306713780284>",
        row=2,
    )
    async def max_channels(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Channel_select(
            placeholder="Select a channel to set as the emoji request channel",
            max_values=1,
            min_values=1,
            channel_types=[discord.ChannelType.text],
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is False or view.value is None:
            return await interaction.delete_original_response()

        self.data["emojis"]["request_channel"] = view.select.values[0].id
        await interaction.client.Perk.update("config", self.data)
        await view.select.interaction.response.edit_message(
            content=f"Emoji request channel set to {view.select.values[0].mention}",
            view=None,
        )
        await self.message.edit(
            embed=await interaction.client.Perk.get_config_embed(
                interaction.guild, self.data
            )
        )

    @button(
        label="Profile",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_logging:1107652646887759973>",
        row=2,
    )
    async def _profile(self, interaction: Interaction, button: Button):
        options = [
            SelectOption(
                label="List",
                description="List all the profiles",
                value="list",
                emoji="<:tgk_entries:1124995375548338176>",
            ),
            SelectOption(
                label="Create",
                description="Create a new profile",
                value="create",
                emoji="<:tgk_color:1107261678204244038>",
            ),
            SelectOption(
                label="Delete",
                description="Delete a profile",
                value="delete",
                emoji="<:tgk_delete:1113517803203461222>",
            ),
        ]

        view = View()
        view.value = False
        view.select = Select_General(
            interaction=interaction, options=options, placeholder="Select an operation"
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is False or view.value is None:
            return await interaction.delete_original_response()

        match view.select.values[0]:
            case "create":
                formated_args = await get_formated_embed(
                    ["Role", "Duration", "Share Limit", "Perk Type"]
                )
                embed = discord.Embed(
                    title="", description="", color=interaction.client.default_color
                )
                embed.description = ""

                embed.description += (
                    "<:tgk_color:1107261678204244038> `Create a new profile`\n\n"
                )
                embed.description += f"{formated_args['Role']} `None`\n"
                embed.description += f"{formated_args['Duration']} `None`\n"
                embed.description += f"{formated_args['Share Limit']} `None`\n"
                embed.description += f"{formated_args['Perk Type']} `None`\n\n"
                embed.description += "<:tgk_hint:1206282482744561744> Use the buttons below to set the profile\n\n"

                profile_create_view = Profile_Manage(
                    self.user, message=interaction.message, new=True
                )
                await view.select.interaction.response.edit_message(
                    embed=embed, view=profile_create_view
                )

                await profile_create_view.wait()
                await self.message.edit(
                    embed=await interaction.client.Perk.get_config_embed(
                        interaction.guild
                    )
                )
                self.data = await interaction.client.Perk.get_data(
                    "config", interaction.guild.id, interaction.user.id
                )
                return

            case "list":
                profile_select = Select_General(
                    interaction=interaction,
                    options=profile_select_options,
                    placeholder="Select a profile type",
                    max_values=1,
                    min_values=1,
                )

                profile_select_view = View()
                profile_select_view.value = False
                profile_select_view.add_item(profile_select)

                await view.select.interaction.response.edit_message(
                    view=profile_select_view, content=None
                )
                await profile_select_view.wait()

                if (
                    profile_select_view.value is False
                    or profile_select_view.value is None
                ):
                    return await interaction.delete_original_response()

                profile_type = profile_select.values[0]
                profiles = self.data["profiles"][profile_type]

                formated_args = await get_formated_embed(
                    ["Role", "Duration", "Share Limit", "Perk Type"]
                )
                pages = []
                for role, data in profiles.items():
                    embed = discord.Embed(
                        description="", color=interaction.client.default_color
                    )
                    embed.description = f"<:tgk_entries:1124995375548338176>  `{profile_select.values[0].capitalize()} Profiles`\n\n"
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Role'], type='role', data=data['role_id'])}\n"
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Duration'], type='time', data=data['duration'])}\n"
                    embed.description += f"{formated_args['Share Limit']} `{'None' if data['share_limit'] is None else data['share_limit']}`\n"

                    pages.append(embed)

                if len(pages) == 0:
                    embed = discord.Embed(
                        description="No profiles found",
                        color=interaction.client.default_color,
                    )
                    await interaction.edit_original_response(embed=embed, view=None)
                    return
                await interaction.delete_original_response()
                await Paginator(profile_select.interaction, pages).start(
                    embeded=True, quick_navigation=False, hidden=True
                )
                return

            case "delete":
                profile_select = Select_General(
                    interaction=interaction,
                    options=profile_select_options,
                    placeholder="Select a profile type",
                    max_values=1,
                    min_values=1,
                )
                profile_select_view = View()
                profile_select_view.value = False
                profile_select_view.add_item(profile_select)

                await view.select.interaction.response.edit_message(
                    view=profile_select_view, content=None
                )
                await profile_select_view.wait()

                if (
                    profile_select_view.value is False
                    or profile_select_view.value is None
                ):
                    return await interaction.delete_original_response()

                profile_type = profile_select.values[0]
                profiles = self.data["profiles"][profile_type]
                options = []
                for pro in profiles.keys():
                    role = interaction.guild.get_role(int(pro))
                    options.append(SelectOption(label=role.name, value=str(role.id)))
                options = options[:24]

                profile_delete = Select_General(
                    interaction=interaction,
                    options=options,
                    placeholder="Select a profile to delete",
                    max_values=len(options),
                    min_values=1,
                )
                profile_delete_view = View()
                profile_delete_view.value = False
                profile_delete_view.add_item(profile_delete)

                await profile_select.interaction.response.edit_message(
                    view=profile_delete_view, content=None
                )
                await profile_delete_view.wait()

                if (
                    profile_delete_view.value is False
                    or profile_delete_view.value is None
                ):
                    return await interaction.delete_original_response()

                for value in profile_delete.values:
                    del self.data["profiles"][profile_type][value]

                await interaction.client.Perk.update("config", self.data)
                await profile_delete.interaction.response.edit_message(
                    content="Profile(s) deleted", view=None
                )
                await self.message.edit(
                    embed=await interaction.client.Perk.get_config_embed(
                        interaction.guild, self.data
                    )
                )


class Profile_Manage(View):
    def __init__(
        self,
        user: discord.Member,
        data: Profile = None,
        message: discord.Message = None,
        type: str = None,
        new=False,
    ):
        self.user = user
        self.data = data
        self.message = message
        self.new = new
        self.type = None
        super().__init__(timeout=120)
        if self.new:
            self.children[0].disabled = False
            self.data: Profile = {
                "role_id": None,
                "duration": "permanent",
                "share_limit": None,
            }

    async def get_embed(self, interaction: Interaction, data: dict):
        formated_args = await get_formated_embed(
            ["Role", "Duration", "Share Limit", "Perk Type"]
        )
        embed = discord.Embed(
            title="", description="", color=interaction.client.default_color
        )
        embed.description = ""
        if self.new:
            embed.description += (
                "<:tgk_color:1107261678204244038> `Create a new profile`\n\n"
            )
        else:
            embed.description += "<:tgk_color:1107261678204244038> `Edit a profile`\n\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Role'], type='role', data=data['role_id'])}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Duration'], type='time', data=data['duration'])}\n"
        embed.description += f"{formated_args['Share Limit']} `{'None' if data['share_limit'] is None else data['share_limit']}`\n"
        embed.description += f"{formated_args['Perk Type']} `{'None' if self.type is None else self.type}`\n\n"

        embed.description += "<:tgk_hint:1206282482744561744> Use the buttons below to set the profile\n\n"

        return embed

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message(
            "You are not the owner of this profile", ephemeral=True
        )
        return False

    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

    @select(
        placeholder="Select a Role for the profile",
        min_values=1,
        max_values=1,
        cls=discord.ui.RoleSelect,
        disabled=True,
    )
    async def role(self, interaction: Interaction, select: Select):
        self.data["role_id"] = select.values[0].id
        select.disabled = True
        await interaction.response.edit_message(
            view=self, embed=await self.get_embed(interaction, self.data)
        )

    @select(
        placeholder="Select share limit for the profile",
        min_values=1,
        max_values=1,
        options=[SelectOption(label=i, value=i) for i in range(1, 11)],
    )
    async def share_limit(self, interaction: Interaction, select: Select):
        self.data["share_limit"] = int(select.values[0])
        select.options = [
            SelectOption(
                label=select.values[0].capitalize(),
                value=select.values[0],
                default=True,
            )
        ]
        select.disabled = True
        await interaction.response.edit_message(
            view=self, embed=await self.get_embed(interaction, self.data)
        )

    @select(
        placeholder="Select Perk Type",
        options=[
            SelectOption(label="Role", value="roles"),
            SelectOption(label="Channel", value="channels"),
            SelectOption(label="Auto React", value="reacts"),
            SelectOption(label="Highligher", value="highlights"),
            SelectOption(label="Emoji", value="emojis"),
        ],
        max_values=1,
        min_values=1,
        disabled=False,
    )
    async def _type(self, interaction: Interaction, select: Select):
        self.type = select.values[0]
        select.options = [
            SelectOption(label=self.type.capitalize(), value=self.type, default=True)
        ]
        select.disabled = True
        if select.values[0] == "roles":
            self.add_item(Top_Profile_toggle())
        await interaction.response.edit_message(
            view=self, embed=await self.get_embed(interaction, self.data)
        )

    @button(
        label="Save",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_save:1210649255501635594>",
    )
    async def save(self, interaction: Interaction, button: Button):
        if not all(
            [
                self.children[0].disabled,
                self.children[1].disabled,
                self.children[2].disabled,
            ]
        ):
            await interaction.response.send_message(
                "You are missing some required fields", ephemeral=True
            )
            return

        config: PerkConfig = await interaction.client.Perk.get_data(
            "config", interaction.guild.id, interaction.user.id
        )
        button.disabled = True
        if str(self.data["role_id"]) in config["profiles"][self.type]:
            await interaction.response.send_message(
                "A profile with the same role already exists", ephemeral=True
            )
        else:
            config["profiles"][self.type][str(self.data["role_id"])] = self.data
            await interaction.client.Perk.update("config", config)
            await interaction.response.edit_message(content="Profile saved", view=self)
        await asyncio.sleep(1.5)
        await interaction.delete_original_response()
        self.stop()


class Top_Profile_toggle(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="Top Profile",
            emoji="<:level_roles:1123938667212312637>",
        )

    async def callback(self, interaction: Interaction):
        self.view.data["top_profile"] = not self.view.data["top_profile"]
        await interaction.response.edit_message(
            view=self.view, embed=await self.view.get_embed(interaction, self.view.data)
        )


class Friends_manage(View):
    def __init__(
        self,
        user: discord.Member,
        data: dict,
        type: str,
        message: discord.Message = None,
    ):
        self.user = user
        self.data = data
        self.message = message
        self.type = type
        self.cd = app_commands.Cooldown(1, 10)
        if type not in ["roles", "channels"]:
            raise ValueError("type must be either roles or channels")
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: Interaction):
        retry_after = self.cd.update_rate_limit()
        if retry_after:
            raise ButtonCooldown(retry_after)

        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message(
                "You are not the owner of this menu", ephemeral=True
            )
            return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            await self.message.edit(view=self)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = "second" if seconds == 1 else "seconds"
            return await interaction.response.send_message(
                f"You're on cooldown for {seconds} {unit}!", ephemeral=True
            )
        try:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
        except discord.HTTPException:
            raise error

    @select(
        placeholder="Select a members to add/remove from your friends",
        max_values=10,
        cls=discord.ui.UserSelect,
        min_values=1,
    )
    async def select(self, interaction: Interaction, select: Select):
        add_friends = []
        remove_friends = []
        await interaction.response.send_message("Processing...", ephemeral=True)
        match self.type:
            case "roles":
                role = interaction.guild.get_role(self.data["role_id"])
                for value in select.values:
                    if value.id == self.data["user_id"]:
                        continue
                    if value.id in self.data["friend_list"] or value in role.members:
                        remove_friends.append(value)
                        await value.remove_roles(
                            role, reason=f"Removed from {self.user.name}'s friends"
                        )
                        try:
                            self.data["friend_list"].remove(value.id)
                        except Exception:
                            pass
                    else:
                        if len(self.data["friend_list"]) >= self.data["share_limit"]:
                            break
                        add_friends.append(value)
                        await value.add_roles(
                            role, reason=f"Added to {self.user.name}'s friends"
                        )
                        self.data["friend_list"].append(value.id)

                res_embed = discord.Embed(
                    title="Friends Updated",
                    color=interaction.client.default_color,
                    description="",
                )
                res_embed.description += f"**Added:** {', '.join([f'<@{friend.id}>' for friend in add_friends]) if add_friends else '`None`'}\n"
                res_embed.description += f"**Removed:** {', '.join([f'<@{friend.id}>' for friend in remove_friends]) if remove_friends else '`None`'}\n"
                await interaction.edit_original_response(embed=res_embed, content=None)

                await interaction.client.Perk.update("roles", self.data)

                up_embed = self.message.embeds[0]
                friends = "".join(
                    [
                        f"<@{friend}> `({friend})`\n"
                        for friend in self.data["friend_list"]
                    ]
                )
                up_embed.set_field_at(
                    0,
                    name="Friends",
                    value=friends if friends else "`No Friends ;(`",
                    inline=False,
                )
                await self.message.edit(embed=up_embed)
                return

            case "channels":
                for value in select.values:
                    if value.id == self.data["user_id"]:
                        continue
                    channel = interaction.guild.get_channel(self.data["channel_id"])
                    if (
                        value in channel.overwrites.keys()
                        or value.id in self.data["friend_list"]
                    ):
                        remove_friends.append(value)
                        await channel.set_permissions(
                            value,
                            overwrite=None,
                            reason=f"Removed from {self.user.name}'s friends",
                        )
                        try:
                            self.data["friend_list"].remove(value.id)
                        except ValueError:
                            pass
                    else:
                        if len(self.data["friend_list"]) >= self.data["share_limit"]:
                            break
                        add_friends.append(value)
                        await channel.set_permissions(
                            value,
                            view_channel=True,
                            reason=f"Added to {self.user.name}'s friends",
                        )
                        self.data["friend_list"].append(value.id)

                res_embed = discord.Embed(
                    title="Friends Updated",
                    color=interaction.client.default_color,
                    description="",
                )
                res_embed.description += f"**Added:** {', '.join([f'<@{friend.id}>' for friend in add_friends]) if add_friends else '`None`'}\n"
                res_embed.description += f"**Removed:** {', '.join([f'<@{friend.id}>' for friend in remove_friends]) if remove_friends else '`None`'}\n"
                await interaction.edit_original_response(embed=res_embed, content=None)

                await interaction.client.Perk.update("channels", self.data)

                up_embed = self.message.embeds[0]
                friends = "".join(
                    [
                        f"<@{friend}> `({friend})`\n"
                        for friend in self.data["friend_list"]
                    ]
                )
                up_embed.set_field_at(
                    0,
                    name="Friends",
                    value=friends if friends else "`No Friends ;(`",
                    inline=False,
                )
                await self.message.edit(embed=up_embed)
                return

    @button(
        label="Sync",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_sync:1145387798099140688>",
    )
    async def sync(self, interaction: Interaction, button: Button):
        match self.type:
            case "roles":
                role = interaction.guild.get_role(self.data["role_id"])
                self.data["friend_list"] = []
                removed = ""
                for member in role.members:
                    if member.id == self.data["user_id"]:
                        continue
                    self.data["friend_list"].append(member.id)
                    if len(self.data["friend_list"]) >= self.data["share_limit"] + 1:
                        await member.remove_roles(
                            role, reason=f"Removed from {self.user.name}'s friends"
                        )
                        removed += f"<@{member.id}> `({member.id})`\n"
                await interaction.client.Perk.update("roles", self.data)
                if removed != "":
                    await interaction.response.send_message(
                        f"Since you have reached the friend limit, the following members were removed from your friends:\n{removed}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Friends synced", ephemeral=True
                    )
            case "channels":
                channel = interaction.guild.get_channel(self.data["channel_id"])
                self.data["friend_list"] = []
                removed = ""
                for targate, perm in channel.overwrites:
                    if not isinstance(targate, discord.Member):
                        continue
                    if targate.id == self.data["user_id"]:
                        continue
                    self.data["friend_list"].append(targate.id)
                    if len(self.data["friend_list"]) >= self.data["share_limit"] + 1:
                        await channel.set_permissions(
                            targate,
                            overwrite=None,
                            reason=f"Removed from {self.user.name}'s friends",
                        )
                        removed += f"<@{targate.id}> `({targate.id})`\n"
                await interaction.client.Perk.update("channels", self.data)
                if removed != "":
                    await interaction.response.send_message(
                        f"Since you have reached the friend limit, the following members were removed from your friends:\n{removed}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Friends synced", ephemeral=True
                    )

    @button(label="Reset Friends", style=discord.ButtonStyle.red)
    async def reset(self, interaction: Interaction, button: Button):
        match self.type:
            case "roles":
                role = interaction.guild.get_role(self.data["role_id"])
                for member in role.members:
                    if member.id != self.data["user_id"]:
                        await member.remove_roles(
                            role, reason=f"Removed from {self.user.name}'s friends"
                        )
                self.data["friend_list"] = []
                await interaction.client.Perk.update("roles", self.data)
                await interaction.response.send_message(
                    "Friends resetted", ephemeral=True
                )

                up_embed = self.message.embeds[0]
                friends = "".join(
                    [
                        f"<@{friend}> `({friend})`\n"
                        for friend in self.data["friend_list"]
                    ]
                )
                up_embed.set_field_at(
                    0,
                    name="Friends",
                    value=friends if friends else "`No Friends ;(`",
                    inline=False,
                )
                await self.message.edit(embed=up_embed)
                return

            case "channels":
                channel = interaction.guild.get_channel(self.data["channel_id"])
                for friends in self.data["friend_list"]:
                    member = interaction.guild.get_member(friends)
                    if member:
                        await channel.set_permissions(
                            member,
                            overwrite=None,
                            reason=f"Removed from {self.user.name}'s friends",
                        )
                self.data["friend_list"] = []
                await interaction.client.Perk.update("channels", self.data)
                await interaction.response.send_message(
                    "Friends resetted", ephemeral=True
                )

                up_embed = self.message.embeds[0]
                friends = "".join(
                    [
                        f"<@{friend}> `({friend})`\n"
                        for friend in self.data["friend_list"]
                    ]
                )
                up_embed.set_field_at(
                    0,
                    name="Friends",
                    value=friends if friends else "`No Friends ;(`",
                    inline=False,
                )
                await self.message.edit(embed=up_embed)
                return

            case _:
                await interaction.response.send_message(
                    "Something went wrong", ephemeral=True
                )
                return


class Perk_Ignore(View):
    def __init__(self, data: dict, message: discord.Message = None):
        super().__init__(timeout=120)
        self.data = data
        self.message = message

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.data["user_id"]:
            return True
        await interaction.response.send_message("This is not your perk", ephemeral=True)
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    async def get_embed(self, data: dict, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Ignore Role/Channel",
            description="",
            color=interaction.client.default_color,
        )
        embed.description += (
            "Users:"
            + f"{', '.join([f'<@{i}>' for i in data['ignore_users']]) if data['ignore_users'] else '`None`'}"
        )
        embed.description += (
            "\nChannels:"
            + f"{', '.join([f'<#{i}>' for i in data['ignore_channel']]) if data['ignore_channel'] else '`None`'}"
        )
        return embed

    @select(
        placeholder="Select users you want to ignore or unignore",
        min_values=1,
        max_values=25,
        cls=discord.ui.UserSelect,
    )
    async def _user(self, interaction: discord.Interaction, select: Select):
        added = ""
        removed = ""
        for value in select.values:
            if value.id in self.data["ignore_users"]:
                self.data["ignore_users"].remove(value.id)
                removed += f"<@{value.id}> `({value.id})`\n"
            else:
                self.data["ignore_users"].append(value.id)
                added += f"<@{value.id}> `({value.id})`\n"
        await interaction.response.edit_message(
            embed=await self.get_embed(self.data, interaction)
        )
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.followup.send(
            f"**Added:**\n{added if added else '`None`'}\n**Removed:**\n{removed if removed else '`None`'}",
            ephemeral=True,
        )

    @select(
        placeholder="Select channels you want to ignore or unignore",
        min_values=1,
        max_values=25,
        cls=discord.ui.ChannelSelect,
    )
    async def _channel(self, interaction: discord.Interaction, select: Select):
        added = ""
        removed = ""
        for value in select.values:
            if value.id in self.data["ignore_channel"]:
                self.data["ignore_channel"].remove(value.id)
                removed += f"<#{value.id}> `({value.id})`\n"
            else:
                self.data["ignore_channel"].append(value.id)
                added += f"<#{value.id}> `({value.id})`\n"
        await interaction.response.edit_message(
            embed=await self.get_embed(self.data, interaction)
        )
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.followup.send(
            f"**Added:**\n{added if added else '`None`'}\n**Removed:**\n{removed if removed else '`None`'}",
            ephemeral=True,
        )

    @button(label="Reset", style=discord.ButtonStyle.red)
    async def reset(self, interaction: Interaction, button: Button):
        self.data["ignore_users"] = []
        self.data["ignore_channel"] = []
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.response.edit_message(
            embed=await self.get_embed(self.data, interaction)
        )
        await interaction.followup.send(
            "Ignored users and channels resetted\nNote: This might take a while to update",
            ephemeral=True,
        )


class Emoji_Request(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        config = await interaction.client.Perk.get_data(
            "config", interaction.guild.id, interaction.user.id
        )
        user_roles = [role.id for role in interaction.user.roles]
        if set(config["admin_roles"]) & set(user_roles):
            return True
        else:
            await interaction.response.send_message(
                "You are not an admin", ephemeral=True
            )
            return False

    @button(
        label="Approve",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_active:1082676793342951475>",
        custom_id="emoji:approve",
    )
    async def approve(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Processing...", ephemeral=True)

        config: Config = await interaction.client.Perk.get_data(
            "config", interaction.guild.id, interaction.user.id
        )
        emojis_data = await interaction.client.Perk.emoji_request.find(
            interaction.message.id
        )
        all_emojis = await interaction.client.Perk.emoji.find_many_by_custom(
            {"guild_id": interaction.guild.id}
        )
        user = interaction.guild.get_member(emojis_data["user_id"])

        if len(all_emojis) >= config["emojis"]["max"]:
            return await interaction.response.send_message(
                "You have reached the max emoji limit", ephemeral=True
            )

        async with aiohttp.ClientSession() as session:
            async with session.get(interaction.message.attachments[0].url) as resp:
                if resp.status != 200:
                    return await interaction.response.send_message(
                        "Failed to download the emoji", ephemeral=True
                    )
                emoji_bytes = await resp.read()
                await session.close()

        user_profile = await interaction.client.Perk.calulate_profile(
            interaction.client.Perk.types.emojis, interaction.guild, interaction.user
        )
        user_data: Custom_Emoji = await interaction.client.Perk.get_data(
            "emojis", interaction.guild.id, interaction.user.id
        )
        if not user_data:
            user_data = await interaction.client.Perk.create(
                "emojis",
                user_id=emojis_data["user_id"],
                guild_id=interaction.guild.id,
                duration="permanent",
                share_limit=user_profile["share_limit"],
            )
        user_data["max_emoji"] = user_profile["share_limit"]

        if len(user_data["emojis"]) >= user_data["max_emoji"]:
            await interaction.client.Perk.emoji_request.delete(emojis_data["_id"])
            await interaction.edit_original_response(
                content="User has reached the max emoji limit", view=None
            )
            await interaction.message.delete()
            try:
                await user.send(
                    "You emoji request has been rejected because you have reached the max emoji limit"
                )
            except discord.HTTPException:
                pass
            return
        emoji_name = (
            emojis_data["name"]
            if "tgk_" in emojis_data["name"]
            else f"tgk_{emojis_data['name']}"
        )
        emoji: discord.Emoji = await interaction.guild.create_custom_emoji(
            name=emoji_name,
            image=emoji_bytes,
            reason=f"Emoji Request Approved by {interaction.user.name}",
        )

        try:
            await user.send(f"Your emoji request has been approved\n{emoji}")
        except discord.HTTPException:
            pass

        user_data["emojis"].append(emoji.id)
        await interaction.client.Perk.update("emojis", user_data)
        await interaction.client.Perk.emoji_request.delete(emojis_data["_id"])
        for cld in self.children:
            cld.disabled = True
        await interaction.edit_original_response(content="Emoji added", view=None)
        await interaction.message.edit(
            content=f"Aproved by {interaction.user.mention}", view=self
        )

    @button(
        label="Reject",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_deactivated:1082676877468119110>",
        custom_id="emoji:reject",
    )
    async def reject(self, interaction: Interaction, button: Button):
        emoji_data = await interaction.client.Perk.emoji_request.find(
            interaction.message.id
        )
        modal = General_Modal(title="Reject Reason", interaction=interaction)
        modal.reason = TextInput(
            label="Reason for rejecting the emoji",
            min_length=1,
            max_length=500,
            required=True,
            style=discord.TextStyle.paragraph,
        )
        modal.add_item(modal.reason)
        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.reason.value:
            await modal.interaction.response.send_message(
                "Processing...", ephemeral=True
            )
            user = interaction.guild.get_member(emoji_data["user_id"])

            try:
                await user.send(
                    f"Your emoji request has been rejected for the following reason:\n{modal.reason.value}"
                )
            except discord.HTTPException:
                pass
            await interaction.client.Perk.emoji_request.delete(emoji_data["_id"])
            await modal.interaction.edit_original_response(
                content="Emoji request rejected", view=None
            )
            await interaction.message.delete()
