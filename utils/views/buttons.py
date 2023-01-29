import discord
from discord.ext import commands
from typing import Union
from discord import Interaction
# Define a simple View that gives us a confirmation menu
class Confirm(discord.ui.View):
	def __init__(self, user: Union[discord.Member, discord.User],timeout: int = 30, message:discord.Message = None):
		super().__init__(timeout=timeout)
		self.value = None
		self.user = user
		self.message = message
		self.interaction: discord.Interaction = None

	async def on_timeout(self):		
		for button in self.children:
			button.disabled = True
		await self.message.edit(view=self)
		self.stop()
	
	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id == self.user.id:
			return True
		else:
			await interaction.response.send_message("This is not your confirmation menu.", ephemeral=True)
			return False
	
	async def on_error(self, error, item, interaction):
		pass

	@discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = True
		self.stop()

	@discord.ui.button(label='No', style=discord.ButtonStyle.grey)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = False
		self.stop()