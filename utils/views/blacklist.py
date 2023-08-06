import discord
import datetime
from discord import Interaction, SelectOption
from discord.ui import View, Button, button, TextInput, Item, RoleSelect
from .selects import Role_select, Select_General, Channel_select
from .buttons import Confirm
from .modal import General_Modal

class Blacklist_Config(View):
    def __init__(self, member: discord.Member, data: dict, message: discord.Message=None):
        self.member = member
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    async def update_message(self, interaction: Interaction, blacklist_data: dict):
        embed = discord.Embed(title=f"{interaction.guild.name} Blacklist Config", color=interaction.client.default_color, description="")
        embed.description += f"**Mod Roles:** {', '.join([f'<@&{role}>' for role in blacklist_data['mod_roles']]) if blacklist_data['mod_roles'] else '`None`'}\n"
        embed.description += f"**Logging Channel:** {interaction.guild.get_channel(blacklist_data['log_channel']).mention if blacklist_data['log_channel'] else '`None`'}\n"
        embed.description += f"**Profiles:** {', '.join([f'`{position.capitalize()}`' for position in blacklist_data['profiles'].keys()]) if blacklist_data['profiles'] else '`None`'}\n"        
        await self.message.edit(embed=embed, view=self)
    
    @button(label="Mod Roles", style=discord.ButtonStyle.gray, custom_id="mod_roles", emoji="<:tgk_staff_manager:1073588769560744078>")
    async def mod_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select("Select Role you want to add or remove", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            add_roles = ""
            remove_roles = ""
            for role in view.select.values:
                if role.id in self.data["mod_roles"]:
                    remove_roles += f"{role.mention}, "
                    self.data["mod_roles"].remove(role.id)
                else:
                    add_roles += f"{role.mention}, "
                    self.data["mod_roles"].append(role.id)
            await interaction.client.blacklist.update_config(interaction.guild_id, self.data)
            await view.select.interaction.response.edit_message(content=f"Added: {add_roles}\nRemoved: {remove_roles}", view=None)
        else:
            await interaction.delete_original_message()
        
        await self.update_message(interaction, self.data)
    
    @button(label="Logging Channel", style=discord.ButtonStyle.gray, custom_id="log_channel", emoji="<:tgk_channel:1073908465405268029>")
    async def log_channel(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Channel_select("Select Channel you want to set as logging channel", max_values=1, min_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            if view.select.values[0].id == self.data["log_channel"]:
                self.data["log_channel"] = None
                await interaction.client.blacklist.update_config(interaction.guild_id, self.data)
                await view.select.interaction.response.edit_message(content=f"Removed {view.select.values[0].mention} as logging channel", view=None)
                await self.update_message(interaction, self.data)
                return
            self.data["log_channel"] = view.select.values[0].id
            await interaction.client.blacklist.update_config(interaction.guild_id, self.data)
            await view.select.interaction.response.edit_message(content=f"Set {view.select.values[0].mention} as logging channel", view=None)
            await self.update_message(interaction, self.data)
        else:
            await interaction.delete_original_message()
    
    @button(label="Profiles", style=discord.ButtonStyle.gray, custom_id="profiles", emoji="<:tgk_staff_post:1074264610015826030>")
    async def profiles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        options = [SelectOption(label="Add Profile", value="add"), SelectOption(label="Remove Profile", value="remove")]
        view.select = Select_General(placeholder="Please select action you want to perform", options=options, max_values=1)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value:
            match view.select.values[0]:
                case "add":
                    modal = General_Modal(title="New Profile Creating form", interaction=view.select.interaction)
                    modal.question = discord.ui.TextInput(label="Profile Name", placeholder="Please enter profile name", min_length=3, max_length=20, style=discord.TextStyle.short)
                    modal.add_item(modal.question)
                    await view.select.interaction.response.send_modal(modal)

                    await modal.wait()

                    if modal.value:
                        view = Profile_create(self.member)
                        await modal.interaction.response.edit_message(view=view)
                        await view.wait()
                        profile_data = view.data
                        profile_data["_id"] = modal.question.value
                        embed = discord.Embed(description="", color=modal.interaction.client.default_color)
                        embed.description += f"**Profile Name:** {profile_data['_id']}\n"
                        embed.description += f"**Create By:** {modal.interaction.guild.get_member(profile_data['create_by']).mention if modal.interaction.guild.get_member(profile_data['create_by']) else '`Unknown`'}\n"
                        embed.description += f"**Create At:** {profile_data['create_at'].strftime('%d %B %Y, %H:%M:%S')}\n"
                        embed.description += f"**Roles Add:** {', '.join([modal.interaction.guild.get_role(role).mention for role in profile_data['role_add']]) if profile_data['role_add'] else '`None`'}\n"
                        embed.description += f"**Roles Remove:** {', '.join([modal.interaction.guild.get_role(role).mention for role in profile_data['role_remove']]) if profile_data['role_remove'] else '`None`'}\n"
                        
                        confim = Confirm(interaction.user, 60)
                        confim.message= await interaction.original_response()
                        confim.children[0].label = "Save"
                        confim.children[1].label = "Cancel"         

                        await view.interaction.response.edit_message(embed=embed, view=confim)
                        await confim.wait()

                        if confim.value:
                            self.data["profiles"][profile_data["_id"]] = profile_data
                            await interaction.client.blacklist.update_config(interaction.guild_id, self.data)
                            await confim.interaction.response.edit_message(content="Profile has been added", view=None)
                            await self.update_message(interaction, self.data)
                        else:
                            await confim.interaction.delete_original_message()
                    else:
                        return
                case "remove":
                    remove = View()
                    remove.value = None
                    options = [SelectOption(label=profile, value=profile) for profile in self.data["profiles"].keys()]
                    remove.select = Select_General(placeholder="Please select profile you want to remove", options=options, max_values=1)
                    remove.add_item(remove.select)
                    await view.select.interaction.response.edit_message(view=remove)
                    await remove.wait()

                    if remove.value:
                        del self.data["profiles"][remove.select.values[0]]
                        await interaction.client.blacklist.update_config(interaction.guild_id, self.data)
                        await remove.select.interaction.response.edit_message(content=f"Removed {remove.select.values[0]} profile", view=None)
                        await self.update_message(interaction, self.data)
                    else:
                        await view.select.interaction.delete_original_message()


class Profile_create(View):
    def __init__(self, member: discord.Member):
        self.data = {
            "_id": None,
            "create_by": member.id,
            "create_at": datetime.datetime.utcnow(),
            "role_add": [],
            "role_remove": [],
        }
        self.member = member
        self.value = None
        self.interaction = None
        super().__init__(timeout=120)
    
    @discord.ui.select(placeholder="Please select roles you want to add", min_values=1, max_values=10, cls=RoleSelect)
    async def role_add(self, interaction: Interaction, select: Role_select):
        self.data["role_add"] = [role.id for role in select.values]
        select.disabled = True
        await interaction.response.edit_message(view=self)
    
    @discord.ui.select(placeholder="Please select roles you want to remove", min_values=1, max_values=10, cls=RoleSelect)
    async def role_remove(self, interaction: Interaction, select: Role_select):
        self.data["role_remove"] = [role.id for role in select.values]
        select.disabled = True
        await interaction.response.edit_message(view=self)
    
    @button(label="Submit", style=discord.ButtonStyle.green, custom_id="submit")
    async def submit(self, interaction: Interaction, button: Button):
        button.disabled = True
        self.value = True
        self.interaction = interaction
        self.stop()
