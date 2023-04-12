import discord
from discord.ext import commands
from discord import app_commands, Interaction

import datetime
import psutil
from typing import Literal
from utils.db import Document
from utils.paginator import Contex_Paginator
from utils.views.member_view import Member_view

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.snipes = {}
        self.bot.esnipes = {}
        self.bot.afk = Document(bot.db, "afk")
        self.bot.votes = Document(bot.db, "Votes")
        self.bot.current_afk = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        current_afks = await self.bot.afk.get_all()
        for afk in current_afks: 
            self.bot.current_afk[afk["_id"]] = afk
    
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
    @app_commands.describe(type="The type of snipe", number="Which # of message do you want to snipe?", hidden="Whether the snipe should be hidden or not")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    async def snipe(self, interaction: Interaction, type: Literal['delete', 'edit'], number: app_commands.Range[int, 1, 10]=1, hidden:bool=False):    
        index = number
        if type == "delete":
            try:
                message = self.bot.snipes[interaction.channel.id]
                message.reverse()
                message = message[index - 1]
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
                message = self.bot.esnipes[interaction.channel.id]
                message.reverse()
                message = message[index - 1]
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
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    async def enter(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{interaction.user}** has entered the room! <:TGK_pepeenter:790189012148682782>")

    @app_commands.command(name="exit", description="Tell everyone that you leave the chat")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
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
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None or message.content is None: 
            return
        if message.author.id in self.bot.current_afk.keys():
            self.bot.dispatch("afk_return", message)
        if len(message.mentions) > 0:
            for user in message.mentions:
                if user.id in self.bot.current_afk.keys() and user in message.channel.members:
                   return self.bot.dispatch("afk_ping", message, user)
        if message.reference is not None:
            try:
                reference_message = await message.channel.fetch_message(message.reference.message_id)
            except:
                return
            if reference_message.author.id in self.bot.current_afk.keys():
                self.bot.dispatch("afk_ping", message, reference_message.author)
    
    @commands.Cog.listener()
    async def on_afk_return(self, message):
        user_data = await self.bot.afk.find(message.author.id)
        
        if user_data is None:
            if '[AFK]' in message.author.display_name:
                try:
                    await message.author.edit(nick=message.author.display_name.replace('[AFK]', ''))
                except discord.Forbidden:
                    pass
            if message.author.id in self.bot.current_afk.keys():
                self.bot.current_afk.pop(message.author.id)
            return
        
        if len(user_data['pings']) != 0:
            embeds = []
            pages = len(user_data['pings'])
            for index,user_data in enumerate(user_data['pings']):
                guild = self.bot.get_guild(user_data['guild_id'])
                user = guild.get_member(user_data['id'])
                pinged_at = user_data['pinged_at']
                jump_url = user_data['jump_url']
                content = user_data['message']
                channel = guild.get_channel(user_data['channel_id'])
                channel_name = channel.name if channel else "Unknown Channel"
                embed = discord.Embed(color=0x2b2d31 , timestamp=user_data['timestamp'])
                embed.set_author(name = f'{user.name}#{user.discriminator}', icon_url = user.avatar.url if user.avatar else user.default_avatar)
                embed.description = f"<a:tgk_redSparkle:1072168821797965926> [`You were pinged in #{channel_name}.`]({jump_url}) {pinged_at}\n"
                embed.description += f"<a:tgk_redSparkle:1072168821797965926> **Message:** {content}"
                embed.set_footer(text = f"Pings you received while you were AFK • Pinged at")
                embeds.append(embed)
            try:
                await message.author.send(embeds=embeds)
            except:
                await message.reply("I couldn't send you the pings you received while you were AFK because you have DMs disabled.", delete_after=10, mention_author=False)
        try:
            await self.bot.afk.delete(message.author.id)
            self.bot.current_afk.pop(message.author.id)
        except KeyError:
            pass
        
        try:
            if "last_nick" in user_data.keys():
                await message.author.edit(nick=user_data['last_nick'])
            else:
                await message.author.edit(nick=message.author.display_name.replace('[AFK]', ''))
        except discord.Forbidden:
            pass
            
        await message.reply(f"Welcome back {message.author.mention}!", delete_after=10)

    @commands.Cog.listener()
    async def on_afk_ping(self, message:discord.Message, user:discord.Member):
        user_data = await self.bot.afk.find(user.id)
        user_data['pings'].append({
            "id":message.author.id,
            "message": message.content if len(message.content) <= 100 else f"{message.content[:100]}...",
            "jump_url": message.jump_url,
            "pinged_at": f'<t:{int(datetime.datetime.timestamp(datetime.datetime.now()))}:R>',
            "timestamp": datetime.datetime.now(),
            "channel_id": message.channel.id,
            "guild_id": message.guild.id
        })
        if len(user_data['pings']) > 10:
            while len(user_data['pings']) > 10:
                user_data['pings'].pop(0)
        await self.bot.afk.update(user_data)
        await message.reply(f"`{user_data['last_nick']}` is afk: {user_data['reason']}", delete_after=10, allowed_mentions=discord.AllowedMentions.none(), mention_author=False)

    @app_commands.command(name="afk", description="Set your afk status")
    @app_commands.describe(reason="The reason for your afk status")
    async def afk(self, interaction: Interaction, reason: str=None):
        user_data = await self.bot.afk.find(interaction.user.id)
        if user_data is not None: 
            await self.bot.afk.delete(interaction.user.id)
        last_nick = interaction.user.display_name if  not interaction.user.display_name.startswith('[AFK]') else interaction.user.display_name.replace('[AFK]', '')
        user_data = {'_id': interaction.user.id,'guild_id': interaction.guild.id,'reason': reason,'last_nick': last_nick,'pings': []}
        await self.bot.afk.insert(user_data)
        await interaction.response.send_message(f"`{interaction.user.display_name}` I set your status to {reason if reason else 'afk'}", ephemeral=True)
        nick = f"[AFK] {interaction.user.display_name}"
        if len(nick) > 32:
            nick = nick[:32]
        try:
            await interaction.user.edit(nick=f"{nick}")
        except discord.Forbidden:
            pass
        self.bot.current_afk[interaction.user.id] = user_data
    
    @app_commands.command(name="whois", description="Get information about a user")
    @app_commands.describe(member="The user to get information about")
    async def whois(self, interaction: Interaction, member: discord.Member=None):
        member = member if member else interaction.user

        embed = discord.Embed(title=f"User Info - {member.name}#{member.discriminator}")
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        embed.add_field(name="<:authorized:991735095587254364> ID:", value=member.id)
        embed.add_field(name="<:displayname:991733326857654312> Display Name:", value=member.display_name)

        embed.add_field(name="<:bot:991733628935610388> Bot Account:", value=member.bot)

        embed.add_field(name="<:settings:991733871118917683> Account creation:", value=member.created_at.strftime('%d/%m/%Y %H:%M:%S'))
        embed.add_field(name="<:join:991733999477203054> Server join:", value=member.joined_at.strftime('%d/%m/%Y %H:%M:%S'))

        if not member.bot:
            view = Member_view(self.bot, member, interaction)
            await interaction.response.send_message(embed=embed,view=view)
            view.message = await interaction.original_response()
        else:
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Basic(bot), guilds=[discord.Object(785839283847954433)])






        
    
