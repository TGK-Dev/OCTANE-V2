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
        embed.add_field(name="Ping", value=f"{(end - start).microseconds / 1000}ms")
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().percent}%")
        embed.add_field(name="Threads", value=f"{psutil.cpu_count()}")
        embed.add_field(name="Uptime", value=f"{(datetime.datetime.now() - self.bot.start_time).days} days, {(datetime.datetime.now() - self.bot.start_time).seconds // 3600} hours, {((datetime.datetime.now() - self.bot.start_time).seconds // 60) % 60} minutes, {((datetime.datetime.now() - self.bot.start_time).seconds) % 60} seconds")

        await interaction.edit_original_response(content=None, embed=embed)
    
    @app_commands.command(name="snipe", description="Snipe a deleted/edited message from the channel")
    @app_commands.describe(type="The type of snipe", index="The index of the snipe", hidden="Whether the snipe should be hidden or not")
    async def snipe(self, interaction: Interaction, type: Literal['delete', 'edit'], index: app_commands.Range[int, 1, 10]=1, hidden:bool=False):    
        if type == "delete":
            try:
                message = self.bot.snipes[interaction.channel.id][index - 1]
            except KeyError:
                return await interaction.response.send_message("No snipes found in this channel", ephemeral=True)
            except IndexError:
                return await interaction.response.send_message("No snipes found on that index", ephemeral=True)

            author = interaction.guild.get_member(message['author'])
            embed = discord.Embed(description=message['content'], color=author.color)
            embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
            embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
            embed.timestamp = datetime.datetime.now()

            await interaction.response.send_message(embed=embed, ephemeral=hidden)

        elif type == "edit":
            try:
                message = self.bot.esnipes[interaction.channel.id][index - 1]
            except KeyError:
                return await interaction.response.send_message("No snipes found in this channel", ephemeral=True)
            except IndexError:
                return await interaction.response.send_message("No snipes found on that index", ephemeral=True)
            
            author = interaction.guild.get_member(message['author'])
            embed = discord.Embed(description=f"**Before:** {message['before']}\n**After:** {message['after']}", color=author.color)
            embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
            embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
            embed.timestamp = datetime.datetime.now()

            await interaction.response.send_message(embed=embed, ephemeral=hidden)
        else:
            return await interaction.response.send_message("Invalid type of snipe provided", ephemeral=True)
        
    @app_commands.command(name="enter", description="Tell everyone that you enter the chat")
    async def enter(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{interaction.user}** has entered the room! <:TGK_pepeenter:790189012148682782>")

    @app_commands.command(name="leave", description="Tell everyone that you leave the chat")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{interaction.user}** has left the room! <:TGK_pepeexit:790189030569934849>")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or message.guild is None or message.content is None: return

        if message.channel.id not in self.bot.snipes.keys():
            self.bot.snipes[message.channel.id] = []
        
        if len(self.bot.snipes[message.channel.id]) == 10:
            self.bot.snipes[message.channel.id].pop(0)
        
        self.bot.snipes[message.channel.id].append({
            "author": message.author.id,
            "content": message.content
        })

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.guild is None or before.content is None: return

        if before.channel.id not in self.bot.esnipes.keys():
            self.bot.esnipes[before.channel.id] = []
        
        if len(self.bot.esnipes[before.channel.id]) == 10:
            self.bot.esnipes[before.channel.id].pop(0)
        
        self.bot.esnipes[before.channel.id].append({
            "author": before.author.id,
            "before": before.content,
            "after": after.content
        })

async def setup(bot):
    await bot.add_cog(Basic(bot))






        
    
