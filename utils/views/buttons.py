import discord
from discord.ext import commands
from typing import Union
from discord import Interaction
from discord.ui import View
# Define a simple View that gives us a confirmation menu
class Confirm(View):
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
	
	async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
		try:
			await interaction.response.send_message(f"An error occured: {error}", ephemeral=True)
		except discord.InteractionResponded:
			await interaction.followup.send(f"An error occured: {error}", ephemeral=True)

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

class Link_view(View):
	def __init__(self, label, url):
		super().__init__(timeout=None)
		self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.url))


class Reload(View):
	def __init__(self, cog: str,message: discord.Message=None):
		self.message = message
		self.cog = cog
		super().__init__(timeout=120)

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id in [488614633670967307, 301657045248114690]:
			return True
		else:
			await interaction.response.send_message("Imagin use this button when you can't even reload me.", ephemeral=True)
			return False
	
	async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
		await interaction.edit_original_response(content=f"An error occured: {error}")
		return

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		await self.message.edit(view=self)
		self.stop()

	@discord.ui.button(emoji="<:reload:1127218199969144893>", style=discord.ButtonStyle.gray, custom_id="DEV:RELOAD")
	async def reload(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message("Reloading...", ephemeral=True)
		try:
			await interaction.client.reload_extension(self.cog)
		except Exception as e:
			await interaction.edit_original_response(content=f"An error occured: {e}")
			return
		await interaction.edit_original_response(content="Reloaded!", view=None)
	

