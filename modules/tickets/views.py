import discord
import traceback
from discord import Interaction, SelectOption, app_commands
from discord.ui import View, Button, button, TextInput, Item, Select, select
from utils.views.selects import Role_select, Select_General, Channel_select
from utils.views.modal import General_Modal
from utils.views.buttons import Confirm
from utils.paginator import Paginator


class TicketConfig(View):
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
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.response.send_message(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        except :
            await interaction.followup.send(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        
    
    @button(label='Admin Role', style=discord.ButtonStyle.gray, emoji='<:tgk_role:1073908306713780284>')
    async def foo(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder='Select the role you want to add/remove', min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()

        