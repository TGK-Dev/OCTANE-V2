import discord
import random
import datetime
from discord.ext import commands
from typing import Union
from discord import Interaction, Button
from discord.ui import View, button
import asyncio

class GuessTheNumber(View):
    def __init__(self, user: discord.Member, max_number: int, req_role: discord.Role = None, message: discord.Message = None):
        self.user = user
        self.max_number = max_number
        self.right_number = None
        self.message = None
        self.req_role = req_role if req_role else None
        super().__init__(timeout=300)
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("This is not your guess the number menu.", ephemeral=True)
            return False
    
    async def on_error(self, error, item, interaction:Interaction):
        await interaction.response.send_message("An error occured while running this command.", ephemeral=True)
    
    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        await self.message.edit(view=self)
        self.stop()

    @button(label='Start Game', style=discord.ButtonStyle.green)
    async def start_game(self, interaction: Interaction, button: Button):
        self.right_number = random.randint(1, self.max_number)
        await interaction.channel.set_permissions(self.user.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=False))
        await interaction.response.send_message(embed=discord.Embed(description="Starting game...", color=interaction.client.default_color), ephemeral=True)

        thread = await interaction.message.create_thread(name=f"Guess The Number | 1-{self.max_number}", auto_archive_duration=1440, reason="Guess The Number", slowmode_delay=5)

        embed = interaction.message.embeds[0]
        new_description = embed.description.split("\n")
        new_description[1] = f"**Thread:** {thread.mention}"
        embed.description = "\n".join(new_description)

        button.label = "Game Started"
        button.style = discord.ButtonStyle.grey
        button.disabled = True

        data = {
            '_id': thread.id,
            'user_id': self.user.id,
            'max_number': self.max_number,
            'right_number': self.right_number,
            'req_role': self.req_role.id if self.req_role else None,
            'channel_id': thread.parent.id,
            'guild_id': thread.parent.guild.id,
            'hints': 0,
            'guesses': 0
        }

        timestamp = round((datetime.datetime.now() + datetime.timedelta(seconds=18)).timestamp())
        thread_message = await thread.send(embed=discord.Embed(description="Starting Game in <t:{}:R>".format(timestamp), color=interaction.client.default_color))
        await interaction.edit_original_response(embed=discord.Embed(description="Game will start in 15s".format(self.max_number), color=interaction.client.default_color))
        await interaction.message.edit(embed=embed, view=self)

        await asyncio.sleep(15)
        await interaction.client.gtn.insert(data)
        interaction.client.gtn_cache[data['_id']] = data
        if self.req_role:
            await interaction.channel.set_permissions(self.req_role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=True))
        else:
            await interaction.channel.set_permissions(self.user.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=True))
        await thread_message.edit(embed=discord.Embed(description="Game has started!\nGuess a number between 1 and {}.".format(self.max_number), color=interaction.client.default_color))
        interaction.client.dispatch("gtn_start", thread, data)