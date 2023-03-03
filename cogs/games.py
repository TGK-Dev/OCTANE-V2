import discord
from discord import app_commands
from discord import Interaction
from discord.ext import commands
from discord.app_commands import Group
from utils.db import Document
from utils.views.gtn import GuessTheNumber
import random
import asyncio
class Games(commands.GroupCog, name="games"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.gtn_cache = {}
        self.bot.games = bot.mongo["Games"]
        self.bot.gtn = Document(self.bot.games, "GuessTheNumber")
    
    gtn = Group(name="gtn", description="Start a game of guess the number")
    
    @gtn.command(name="start", description="Start a game of guess the number")
    @app_commands.describe(max_number="The maximum number to guess from", requried_role="The role required to play the game", prize="The prize for the game")
    async def gtn_start(self, interaction:Interaction, max_number: app_commands.Range[int, 50, 10000], requried_role: discord.Role = None, prize: str = None):
        await interaction.response.send_message(embed=discord.Embed(description="Setting up game of guess the number...", color=self.bot.default_color), ephemeral=True)
        embed = discord.Embed(description="", title="Guess the number", color=self.bot.default_color)
        embed.description += f"**Max Number:** {max_number}\n"
        embed.description += f"**Thread:** `Waiting for host to start game`\n"
        embed.description += f"**Host:** {interaction.user.mention}\n"
        embed.description += f"**Right Number:** `Waiting for host to start game`\n"
        embed.description += f"**Guesses:** `Waiting Game to end`\n"
        if prize:
            embed.description += f"Prize: {prize}\n"
        
        if requried_role:
            embed.description += f"**Required Role:** {requried_role.mention}\n"

        view = GuessTheNumber(interaction.user, max_number, req_role=requried_role)
        msg = await interaction.followup.send(embed=embed, ephemeral=False, view=view)
        view.message = msg
        await interaction.delete_original_response()
    
    @gtn.command(name="end", description="End a game of guess the number")
    @app_commands.describe(thread="The thread to end the game in")
    async def gtn_end(self, interaction:Interaction, thread: discord.Thread):
        data = await self.bot.gtn.find({"_id": thread.id})
        if not data: await interaction.response.send_message(embed=discord.Embed(description="This thread is not a game of guess the number!", color=self.bot.default_color), ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(description="Ending game of guess the number...", color=self.bot.default_color))
            if data["req_role"] != None:
                role = interaction.guild.get_role(data["req_role"])
                await thread.parent.set_permissions(role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=None))
            await thread.parent.set_permissions(interaction.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=False))
            await thread.send(embed=discord.Embed(description=f"The game of guess the number has ended! The right number was `{data['right_number']}` total guesses: `{data['guesses']}`", color=self.bot.default_color))
            await self.bot.gtn.delete({"_id": thread.id})
            try:
                del self.bot.gtn_cache[thread.id]
            except KeyError:
                pass
            await interaction.edit_original_response(embed=discord.Embed(description="Game of guess the number has ended!", color=self.bot.default_color))
    
    @gtn.command(name="hint", description="Get a hint for the game of guess the number")
    @app_commands.describe(thread="The thread to get the hint in")
    async def gtn_hint(self, interaction:Interaction, thread: discord.Thread):
        data = await self.bot.gtn.find({"_id": thread.id})
        if not data: return await interaction.response.send_message(embed=discord.Embed(description="This thread is not a game of guess the number!", color=self.bot.default_color), ephemeral=True)
        if data['user_id'] != interaction.user.id: return await interaction.response.send_message(embed=discord.Embed(description="You are not the host of this game!", color=self.bot.default_color), ephemeral=True)
        if data["hints"] >= 3: return await interaction.response.send_message(embed=discord.Embed(description="You have already used all your hints!", color=self.bot.default_color), ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(description="Getting hint...", color=self.bot.default_color), ephemeral=True)
            right_number = data["right_number"]
            #create a random hint based on the right number
            start_hint = random.randint(0, right_number)
            end_hint = random.randint(right_number, data["max_number"])

            await thread.send(embed=discord.Embed(description=f"Hint: The number is between `{start_hint}` and `{end_hint}`", color=self.bot.default_color))
            await interaction.edit_original_response(embed=discord.Embed(description="Hint has been sent!", color=self.bot.default_color))
            data['hints'] += 1
            await self.bot.gtn.update({"_id": thread.id}, data)

class Games_BackEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def gtn_check(self, m):
        if m.channel.id not in self.bot.gtn_cache.keys():
            pass
        else:
            data = self.bot.gtn_cache[m.channel.id]
            if data != None:
                try:
                    int(m.content)
                    if m.content == str(self.bot.gtn_cache[m.channel.id]["right_number"]) and m.author.id != self.bot.user.id and m.author.id != self.bot.gtn_cache[m.channel.id]["user_id"]:
                        self.bot.dispatch("gtn_end", data, m, m.channel)
                        return True
                    else:
                        self.bot.gtn_cache[m.channel.id]["guesses"] += 1
                        if int(m.content) > self.bot.gtn_cache[m.channel.id]["max_number"]:                        
                            self.bot.dispatch("gtn_out_of_range", m, data)
                        self.bot.dispatch("gtn_update", self.bot.gtn_cache[m.channel.id])
                except ValueError:
                    pass
            
    
    @commands.Cog.listener()
    async def on_gtn_start(self, thread: discord.Thread, data: dict):
        try:
            msg = await self.bot.wait_for("message", check=self.gtn_check, timeout=3600)
        except asyncio.TimeoutError:
            await thread.parent.send(embed=discord.Embed(description="The game of guess the number has timed out!", color=self.bot.default_color))
            await thread.parent.set_permissions(msg.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages_in_threads=False))
            try:
                await self.bot.gtn.delete({"_id": data["_id"]})
                del self.bot.gtn_cache[thread.parent.id]
            except KeyError:
                pass
    
    @commands.Cog.listener()
    async def on_gtn_out_of_range(self, m: discord.Message, data: dict):
        await m.reply(f"Your guess is out of range! The range is `1-{data['max_number']}`")
    
    @commands.Cog.listener()
    async def on_gtn_update(self, data: dict):
        await self.bot.gtn.update({"_id": data["_id"]}, data)
    
    @commands.Cog.listener()
    async def on_gtn_end(self, data: dict, message: discord.Message, thread: discord.Thread):
        if data["req_role"] != None:
            user_roles = [role.id for role in message.author.roles]
            if data["req_role"] not in user_roles: 
                print("not in roles")
                return
        await message.reply(embed=discord.Embed(description=f"`🏆` {message.author.mention} has won the game of guess the number!", color=self.bot.default_color))
        await thread.parent.send(embed=discord.Embed(description=f"`🏆` {message.author.mention} has won the game of guess the number in {thread.mention}!", color=self.bot.default_color))

        message = await thread.parent.fetch_message(thread.id)
        embed = message.embeds[0]
        embed_new_desc =  embed.description
        embed_new_desc = embed_new_desc.split("\n")
        embed_new_desc[3] = f"**Right Number:** {data['right_number']}"
        embed_new_desc[4] = f"**Guesses:** {data['guesses']}"
        embed_new_desc = "\n".join(embed_new_desc)
        embed.description = embed_new_desc
        embed.set_footer(text="This Game has ended and threads are now locked for this channel")
        if data['req_role'] != None:
            role = message.guild.get_role(data['req_role'])
            await thread.parent.set_permissions(role, discord.PermissionOverwrite(send_messages_in_threads=None))
        await thread.parent.set_permissions(message.guild.default_role, discord.PermissionOverwrite(send_messages_in_threads=False))
        await message.edit(embed=embed)
        await thread.edit(name=f"{thread.name} (Ended)")
        await self.bot.gtn.delete({"_id": data["_id"]})
        try:
            del self.bot.gtn_cache[thread.parent.id]
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        for data in await self.bot.gtn.get_all():
            self.bot.gtn_cache[data["_id"]] = data
            guild = self.bot.get_guild(data["guild_id"])
            thread = guild.get_thread(data["_id"])
            if thread:
                self.bot.dispatch("gtn_start", thread, data)

async def setup(bot):
    await bot.add_cog(Games(bot))
    await bot.add_cog(Games_BackEnd(bot))