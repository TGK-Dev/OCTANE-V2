import discord
from discord.ext import commands
from discord import app_commands, Interaction

import datetime
import psutil
from typing import Literal

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.snipes = {}
        self.bot.esnipes = {}
    
    @app_commands.command(name="stats")
    async def stats(self, interaction: Interaction):
        start = datetime.datetime.now()
        await interaction.response.send_message("Pong!")
        end = datetime.datetime.now()

        embed = discord.Embed(title="Bot Stats", description="Bot stats", color=0x00ff00)
        embed.add_field(name="Ping", value=f"{(end - start).microseconds / 1000}ms", inline=False)
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%", inline=False)
        embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().percent}%", inline=False)
        embed.add_field(name="Threads", value=f"{psutil.cpu_count()}", inline=False)
        embed.add_field(name="Uptime", value=f"{(datetime.datetime.now() - self.bot.start_time).days} days, {(datetime.datetime.now() - self.bot.start_time).seconds // 3600} hours, {((datetime.datetime.now() - self.bot.start_time).seconds // 60) % 60} minutes, {((datetime.datetime.now() - self.bot.start_time).seconds) % 60} seconds", inline=False)

        await interaction.edit_original_response(content=None, embed=embed)
    
    @app_commands.command(name="snipe", description="Snipe a deleted/edited message from the channel")
    @app_commands.describe(type="The type of snipe", index="The index of the snipe", hidden="Whether the snipe should be hidden or not")
    async def snipe(self, interaction: Interaction, type: Literal['delete', 'edit'], index: app_commands.Range[int, 1, 10], hidden:bool=False):
        if interaction.channel.id not in self.bot.snipes.keys() or interaction.channel.id not in self.bot.esnipes.keys():
            return await interaction.response.send_message("There are no snipes in this channel", ephemeral=True)
        
        if type == "delete":
            try:
                message = self.bot.snipes[interaction.channel.id][index - 1]
            except IndexError:
                return await interaction.response.send_message("No snipes found on that index", ephemeral=True)
            
            author = interaction.guild.get_member(message['author'])
            embed = discord.Embed(description=message['content'], color=author.color)
            embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)

            await interaction.response.send_message(embed=embed, ephemeral=hidden)

        if type == "edit":
            try:
                message = self.bot.esnipes[interaction.channel.id][index - 1]
            except IndexError:
                return await interaction.response.send_message("No snipes found on that index", ephemeral=True)
            
            author = interaction.guild.get_member(message['author'])
            embed = discord.Embed(description=f"**Before:** {message['before']}\n**After:** {message['after']}", color=author.color)
            embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)

            await interaction.response.send_message(embed=embed, ephemeral=hidden)
        
    @app_commands.command(name="enter", description="Tell everyone that you enter the chat")
    async def enter(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{interaction.user}** has entered the room! <:TGK_pepeenter:790189012148682782>")

    @app_commands.command(name="leave", description="Tell everyone that you leave the chat")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{interaction.user}** has left the room! <:TGK_pepeexit:790189030569934849>")


async def setup(bot):
    await bot.add_cog(Basic(bot))






        
    
