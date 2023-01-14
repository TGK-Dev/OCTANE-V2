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

	@discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = True
		self.stop()

	@discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = False
		self.stop()


class Payout_Buttton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Payout", style=discord.ButtonStyle.green, custom_id="payout")
    async def payout(self, interaction: discord.Interaction, button: discord.ui.Button):
        loadin_embed = discord.Embed(description="<a:loading:998834454292344842> | Marking payout...", color=discord.Color.blue())
        await interaction.response.send_message(embed=loadin_embed, ephemeral=True)

        data = await interaction.client.payout_queue.find(interaction.message.id)
        if not data: await interaction.edit_original_response(embed=discord.Embed(description="<:dynoError:1000351802702692442> | Payout not found in Database", color=discord.Color.red()))

        embed = interaction.message.embeds[0]
        embed.remove_field(len(embed.fields)-1)
        embed.add_field(name="Payout Status", value="**<:nat_reply_cont:1011501118163013634> Done**")
        embed.title = "Successfull Payment!"
        embed.color = discord.Color.green()
        embed.add_field(name="Santioned By", value=f"**<:nat_reply_cont:1011501118163013634> {interaction.user.mention}**")
        button.disabled = True
        button.label = "Payout Successfully!"

        
        winner_channel = interaction.client.get_channel(data['channel'])
        winner_message = await winner_channel.fetch_message(data['winner_message_id'])
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=f'Winner Message', url=f"{winner_message.jump_url}"))
        view.add_item(discord.ui.Button(label=f'Payout Queue Message', url=f"{interaction.message.jump_url}"))
        success_embed = discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Marked Successfully!", color=discord.Color.green())
        await interaction.edit_original_response(embed=success_embed, view=view)
        await interaction.message.edit(view=self, embed=embed, content=None)
        await interaction.client.payout_queue.delete(data['_id'])
        
        is_more_payout_pending = await interaction.client.payout_queue.find_many_by_custom({'winner_message_id': data['winner_message_id']})
        if len(is_more_payout_pending) <= 0:
            loading_emoji = await interaction.client.emoji_server.fetch_emoji(998834454292344842)
            paid_emoji = await interaction.client.emoji_server.fetch_emoji(1052528036043558942)
            winner_channel = interaction.client.get_channel(data['channel'])
            try:
                winner_message = await winner_channel.fetch_message(data['winner_message_id'])
                await winner_message.remove_reaction(loading_emoji, interaction.client.user)
                await winner_message.add_reaction(paid_emoji)
            except Exception as e:
                pass                

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except:
            await interaction.edit_original_response(content=f"Error: {error}")

    async def interaction_check(self, interaction: Interaction):
        config = await interaction.client.payout_config.find(interaction.guild.id)
        roles = [role.id for role in interaction.user.roles]
        if (set(roles) & set(config['manager_roles'])): return True
        else:
            embed = discord.Embed(title="Error", description="You don't have permission to use this button", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False