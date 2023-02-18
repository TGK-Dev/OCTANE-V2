import discord
import datetime
from discord import Interaction, SelectOption, TextStyle
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select, User_Select
from .modal import General_Modal

class Staff_config_edit(View):
    def __init__(self, user: discord.Member, data: dict, message: discord.Message=None):
        self.user = user
        self.message = message
        self.data = data
        self.value = False
        super().__init__(timeout=120)
    
    async def update_embed(self, data: dict, interaction: Interaction):
        embed = discord.Embed(title=f"{interaction.guild.name}'s Staff Settings", description="")
        embed.description += f"**Owners:** {', '.join([f'<@{owner}>' for owner in data['owners']])}\n"
        embed.description += f"**Staff Manager:** {', '.join([f'<@{manager}>' for manager in data['staff_manager']]) if data['staff_manager'] else '`None`'}\n"
        embed.description += f"**Base Role:**" + (f" <@&{data['base_role']}>" if data['base_role'] != None else "`None`") + "\n"
        embed.description += f"**Leave Role:**" + (f" <@&{data['leave_role']}>" if data['leave_role'] != None else "`None`") + "\n"        
        embed.description += f"**Leave Channel:**" + (f" <#{data['leave_channel']}>" if data['leave_channel'] != None else "`None`") + "\n"
        embed.description += f"**Max Positions:** {data['max_positions']}\n"
        embed.description += f"**Last Edit:** " + f"<t:{round(data['last_edit'].timestamp())}:R>\n" if data['last_edit'] else "`None`\n"
        embed.description += f"**Positions:** {', '.join([f'`{position.capitalize()}`' for position in data['positions'].keys()])}\n"
        return embed

    @button(label="Owners", style=discord.ButtonStyle.gray, emoji="<:tgk_owner:1073588580796092558>", row=0)
    async def owners(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = User_Select(placeholder="Please select the owners you want to add/remove", min_values=1, max_values=5)
        view.add_item(view.select)
        
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)

        await view.wait()
        if view.value:
            selected_users = [user.id for user in view.select.values]
            addeed_owners, removed_owners = "", ""
            for user in selected_users:
                if user not in self.data['owners']:
                    self.data['owners'].append(user)
                    addeed_owners += f"<@{user}> "
                else:
                    self.data['owners'].remove(user)
                    removed_owners += f"<@{user}> "
            self.data['last_edit'] = datetime.datetime.now()
            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
            await view.select.interaction.response.edit_message(embed=discord.Embed(description=f"**Added Owners:** {addeed_owners}\n**Removed Owners:** {removed_owners}", color=0x2b2d31), view=None)
            await self.message.edit(embed=await self.update_embed(self.data, interaction))
    
    @button(label="Staff Manager", style=discord.ButtonStyle.gray, emoji="<:tgk_staff_manager:1073588769560744078>", row=0)
    async def staff_manager(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = User_Select(placeholder="Please select the users you want to add/remove", min_values=1, max_values=5)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            selected_users = [user.id for user in view.select.values]
            addeed_users, removed_users = "", ""
            for user in selected_users:
                if user not in self.data['staff_manager']:
                    self.data['staff_manager'].append(user)
                    addeed_users += f"<@{user}> "
                else:
                    self.data['staff_manager'].remove(user)
                    removed_users += f"<@{user}> "
            self.data['last_edit'] = datetime.datetime.now()
            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(self.data, interaction))
    
    @button(label="Base Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=1)
    async def base_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Please select the base role", min_values=1, max_values=1)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            self.data['base_role'] = view.select.values[0].id
            self.data['last_edit'] = datetime.datetime.now()
            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(self.data, interaction))

            
    
    @button(label="Leave Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=1)
    async def leave_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Please select the leave role", min_values=1, max_values=1)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            self.data['leave_role'] = view.select.values[0].id
            self.data['last_edit'] = datetime.datetime.now()
            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(self.data, interaction))

            
    
    @button(label="Leave Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=2)
    async def leave_channel(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Channel_select(placeholder="Please select the leave channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            self.data['leave_channel'] = view.select.values[0].id
            self.data['last_edit'] = datetime.datetime.now()
            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(self.data, interaction))
            
            
    
    @button(label="Positions", style=discord.ButtonStyle.gray, emoji="<:tgk_staff_post:1074264610015826030>", row=2)
    async def positions(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        options = [SelectOption(label="Add Position", value="add"), SelectOption(label="Remove Position", value="remove")]
        view.select = Select_General(placeholder="Please select action you want to perform", options=options, max_values=1)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value:
            match view.select.values[0]:
                case "add":
                    position = {'name': None, 'role': None, 'owner_only': None}
                    modal = General_Modal(title="New Position Creating form", interaction=view.select.interaction)
                    modal.question = TextInput(label="Enter the name of the position", placeholder="Position Name", min_length=1, max_length=20, style=TextStyle.short)
                    modal.add_item(modal.question)
                    await view.select.interaction.response.send_modal(modal)
                    await modal.wait()

                    if modal.value:
                        if modal.question.value in self.data['positions'].keys(): return await modal.question.interaction.response.edit_message(embed=discord.Embed(description="This position already exists", color=0x2b2d31), view=None)
                        position['name'] = modal.question.value
                        view = View()
                        view.value = False
                        view.select = Role_select(placeholder="Please select the role for the position", min_values=1, max_values=1)
                        view.add_item(view.select)
                        await modal.interaction.response.edit_message(embed=discord.Embed(description="Please select the role for the position", color=0x2b2d31), view=view)
                        await view.wait()
                        if view.value:
                            role = view.select.values[0]
                            position['role'] = role.id
                            if role.permissions.administrator or role.permissions.manage_guild:
                                position['owner_only'] = True
                            self.data['positions'][position['name']] = position
                            self.data['last_edit'] = datetime.datetime.now()
                            await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
                            await view.select.interaction.response.edit_message(embed=discord.Embed(description=f"**Added Position:** `{position['name'].capitalize()}`\n**Role:** <@&{position['role']}>\n**Owner Only:** {position['owner_only']}", color=0x2b2d31), view=None)
                            await self.message.edit(embed=await self.update_embed(self.data, interaction))

                case "remove":
                    delete_view = View()
                    delete_view.value = False
                    delete_view.select = Select_General(placeholder="Please select the position you want to remove", options=[SelectOption(label=position.capitalize(), value=position) for position in self.data['positions'].keys()], max_values=1)
                    delete_view.add_item(delete_view.select)
                    await view.select.interaction.response.edit_message(view=delete_view)
                    await delete_view.wait()

                    if delete_view.value:
                        position = delete_view.select.values[0]
                        self.data['positions'].pop(position)
                        self.data['last_edit'] = datetime.datetime.now()
                        await interaction.client.staff_db.config_collection.update(interaction.guild.id, self.data)
                        await delete_view.select.interaction.response.edit_message(embed=discord.Embed(description=f"**Removed Position:** `{position.capitalize()}`", color=0x2b2d31), view=None)
                        await self.message.edit(embed=await self.update_embed(self.data, interaction))
