import discord
import datetime
from discord import Interaction, SelectOption, TextStyle
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select, User_Select
from .modal import General_Modal

class PerkConfig(View):
    def __init__(self, user:discord.Member, data:dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this perk", ephemeral=True)
            return False
    
    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        raise error
    
    async def update_embed(self, interaction: Interaction, data):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color, description="")
        embed.description += f"Custom Category: {interaction.guild.get_channel(data['custom_category']).mention if data['custom_category'] else '`None`'}\n"
        embed.description += f"Custom Roles Position: `{data['custom_roles_position']}`\n"
        return embed
    
    @button(label="Custom Category", style=discord.ButtonStyle.gray, emoji="<:tgk_category:1076602579846447184>")
    async def custom_category(self, interaction: Interaction, button: Button):
        view = View()
        view.select = Channel_select(placeholder="Select a category for custom channels", max_values=1, channel_types=[discord.ChannelType.category], min_values=1)
        view.value = False
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data['custom_category'] = view.select.values[0].id
            await interaction.delete_original_response()
            await interaction.client.perk.update('config',self.data)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
        
    @button(label="Custom Roles Position", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def custom_roles_position(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Select a role to set the position of custom roles", max_values=1, min_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            position = view.select.values[0].position
            if position >= interaction.guild.me.top_role.position:
                return await view.select.interaction.edit_original_response(content="You can't set the position of custom roles to a role higher than your top role", view=None)
            if position == interaction.guild.default_role.position:
                return await view.select.interaction.edit_original_response(content="You can't set the position of custom roles to the default role", view=None)
            
            self.data['custom_roles_position'] = position - 1
            await interaction.client.perk.update('config',self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(interaction, self.data))