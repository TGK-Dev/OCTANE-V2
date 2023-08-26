import discord
from discord.ext import commands
from discord import app_commands, Interaction
import asyncio
import datetime
import psutil
from typing import Literal
from utils.db import Document
from utils.paginator import Paginator
from utils.views.member_view import Member_view

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.snipes = {}
        self.bot.esnipes = {}
        self.bot.votes = Document(bot.db, "Votes")

    
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
    @app_commands.describe(type="The type of snipe", index="Which # of message do you want to snipe?", hidden="Whether the snipe should be hidden or not")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    @app_commands.rename(index="number")
    async def snipe(self, interaction: Interaction, type: Literal['delete', 'edit'], index: app_commands.Range[int, 1, 10]=None, hidden:bool=False):    
        match type:
            case "delete":
                if index is None:
                    try:
                        messages = self.bot.snipes[interaction.channel.id]
                        messages.reverse()
                    except KeyError:
                        embed = discord.Embed(description="There is nothing to snipe!", color=interaction.client.default_color)
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    except Exception as e:
                        embed = discord.Embed(description=f"That message doesn't exist!", color=interaction.client.default_color)
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    pages = []
                    for message in messages:
                        author = interaction.guild.get_member(message['author'])
                        if author is None:
                            author = await self.bot.fetch_user(message['author'])
                        embed = discord.Embed(description=message['content'], color=message['color'])
                        embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
                        embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
                        if message['attachments']:
                            embed.set_image(url=message['attachments'])
                        pages.append(embed)
                    
                    return await Paginator(interaction, pages).start(embeded=True, quick_navigation=False, hidden=hidden)
                else:
                    try:
                        message = self.bot.snipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except KeyError:
                        embed = discord.Embed(description="There is nothing to snipe!", color=interaction.client.default_color)
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    author = interaction.guild.get_member(message['author'])
                    if author is None:
                        author = await self.bot.fetch_user(message['author'])
                    embed = discord.Embed(description=message['content'], color=message['color'])
                    embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
                    embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
                    if message['attachments']:
                        embed.set_image(url=message['attachments'])
                    embed.timestamp = datetime.datetime.now()

                    return await interaction.response.send_message(embed=embed, ephemeral=hidden)

            case "edit":
                if index is None:
                    try:
                        message = self.bot.esnipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except:
                        embed = discord.Embed(description=f"That message doesn't exist!", color=interaction.client.default_color)
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    for message in messages:

                        author = interaction.guild.get_member(message['author'])
                        embed = discord.Embed(description=f"**Before:**\n{message['before']}\n\n**After:**\n{message['after']}", color=author.color if author != None else self.bot.default_color)
                        embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
                        embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
                        
                        pages.append(embed)
                        return await Paginator(interaction, pages).start(embeded=True, quick_navigation=False, hidden=hidden)
                else:
                    try:
                        message = self.bot.esnipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except:
                        embed = discord.Embed(description=f"That message doesn't exist!", color=interaction.client.default_color)
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    author = interaction.guild.get_member(message['author'])
                    embed = discord.Embed(description=f"**Before:**\n{message['before']}\n\n**After:**\n{message['after']}", color=author.color if author != None else self.bot.default_color)
                    embed.set_author(name=author, icon_url=author.avatar.url if author.avatar else author.default_avatar)
                    embed.set_footer(text=f"Sniped by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
                    
                    return await interaction.response.send_message(embed=embed, ephemeral=hidden)
        
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
        data = {
            "author": message.author.id,
            "content": message.content,
            "attachments": [],
            "color": message.author.color
        }
        if len(message.attachments) > 0:
            if message.attachments[0].url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                data["attachments"] = message.attachments[0].url
        self.bot.snipes[message.channel.id].append(data)

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
            "after": after.content,
            "color": before.author.color
        })   
    
    @app_commands.command(name="whois", description="Get information about a user")
    @app_commands.describe(member="The user to get information about")
    async def whois(self, interaction: Interaction, member: discord.Member=None):
        member = member if member else interaction.user

        embed = discord.Embed(title=f"User Info - {member.global_name}")
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


class Appeal_server(commands.GroupCog, name="appeal"):
    def __init__(self, bot):
        self.bot = bot
    

    @app_commands.command(name="reason", description="Get the reason for your ban")
    @app_commands.describe(member="The member to get the reason for")
    @app_commands.checks.has_permissions(ban_members=True)
    async def reason(self, interaction: Interaction, member: discord.Member):
        main_server = self.bot.get_guild(785839283847954433)
        try:
            ban = await main_server.fetch_ban(member)
        except discord.NotFound:
            return await interaction.response.send_message(f"{member.mention} is not banned", ephemeral=True)
        
        await interaction.response.send_message(f"The reason for {member.mention}'s ban is: {ban.reason if ban.reason else 'No reason provided'}", ephemeral=False)
    
    @app_commands.command(name="aproove", description="Aproove an appeal")
    @app_commands.describe(member="The member to aproove", reason="The reason for aprooving the appeal")
    @app_commands.checks.has_permissions(ban_members=True)
    async def aproove(self, interaction: Interaction, member: discord.Member, reason: str):
        main_server = self.bot.get_guild(785839283847954433)
        try:
            ban = await main_server.fetch_ban(member)
        except discord.NotFound:
            return await interaction.response.send_message(f"{member.mention} is not banned", ephemeral=True)
        
        await main_server.unban(member, reason=reason)

        await interaction.response.send_message(f"{member.mention} You have been unbanned from {main_server.name} for the reason: {reason}\nYou can now rejoin the server at https://discord.gg/tgk", ephemeral=False)



class Afk(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.afk = Document(bot.db, "afk")
        self.bot.current_afk = {}

    @commands.Cog.listener()
    async def on_ready(self):
        current_afks = await self.bot.afk.get_all()
        for afk in current_afks: 
            self.bot.current_afk[afk["_id"]] = afk
    
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
                user: discord.Member = guild.get_member(user_data['id'])
                pinged_at = user_data['pinged_at']
                jump_url = user_data['jump_url']
                content = user_data['message']
                channel = guild.get_channel(user_data['channel_id'])
                channel_name = channel.name if channel else "Unknown Channel"
                embed = discord.Embed(color=0x2b2d31 , timestamp=user_data['timestamp'])
                embed.set_author(name = f'{user.global_name if user.global_name != None else user.display_name}', icon_url = user.avatar.url if user.avatar else user.default_avatar)
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
    
    @app_commands.command(name="set", description="Set your afk status")
    @app_commands.describe(reason="The reason for being afk")
    async def _set(self, interaction: Interaction, reason: str=None):
        if len(reason.split(" ")) > 30: 
            return await interaction.response.send_message("Your afk status can only be 30 words long", ephemeral=True)
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
    
    @app_commands.command(name="remove", description="Remove a member from afk")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to remove from afk")
    async def _remove(self, interaction: Interaction, member: discord.Member):
        user_data = await self.bot.afk.find(member.id)
        if user_data is None:
            return await interaction.response.send_message(f"{member.mention} is not afk", ephemeral=True)
        await self.bot.afk.delete(member.id)
        await interaction.response.send_message(f"Successfully removed {member.mention} from afk", ephemeral=True)
        try:
            if "last_nick" in user_data.keys():
                await member.edit(nick=user_data['last_nick'])
            else:
                await member.edit(nick=member.display_name.replace('[AFK]', ''))
        except discord.Forbidden:
            pass
        try:
            self.bot.current_afk.pop(member.id)
        except KeyError:
            pass       

class Ban_battle(commands.GroupCog, name="banbattle"):
    def __init__(self, bot):
        self.bot = bot
        self.battle_guild: discord.Guild = None
        self.battle_data = {}
    
    staff = app_commands.Group(name="staff", description="Staff commands for the ban battle")
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.battle_guild = await self.bot.fetch_guild(1118244586008084581)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != self.battle_guild.id: return
        if member.bot: await member.kick(reason="Bots are not allowed in the ban battle")
        if member.id == self.battle_data['host']:
            role = self.battle_guild.get_role(1118486572115959820)
            await member.add_roles(role)
    
    @staff.command(name="setup", description="Setup the ban battle")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: Interaction):
        if interaction.guild.id == self.battle_guild.id:
            return await interaction.response.send_message("You can't setup the ban battle in the ban battle server", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="<a:loading:1004658436778229791> Setting up the ban battle..."), ephemeral=True)
        over_write = {
            self.battle_guild.default_role: discord.PermissionOverwrite(send_messages=False),
            self.battle_guild.get_role(1118486572115959820): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        battle_channel = await self.battle_guild.create_text_channel(name="Battle-ground", topic="The battle ground for the ban battle", category=self.battle_guild.get_channel(1118244586008084584), overwrites=over_write)
        inv = battle_channel.create_invite(max_usse=100)
        view = discord.ui.View()        
        view.add_item(discord.ui.Button(label="Join", style=discord.ButtonStyle.url, url=inv.url))
        self.battle_data["channel"] = battle_channel
        self.battle_data["inv"] = inv.url
        self.battle_data["host"] = interaction.user.id
        await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully setup the ban battle tap button below to join"), ephemeral=True, view=view)
    
    @staff.command(name="clean-up", description="Clean up the ban battle")
    @app_commands.checks.has_permissions(administrator=True)
    async def clean_up(self, interaction: Interaction):
        await interaction.response.send_message(embed=discord.Embed(description="<a:loading:1004658436778229791> Cleaning up the ban battle..."), ephemeral=True)
        async for ban in self.battle_guild.bans(limit=None):
            if ban.user.reason != "Eliminated from the ban battle": continue
            await self.battle_guild.unban(ban.user, reason="Ban battle clean up")
            await asyncio.sleep(1)
        for member in self.battle_guild.members:
            if member.id == self.battle_data['host']: continue
            await member.kick(reason="Ban battle clean up")
            await asyncio.sleep(1)
        for invites in await self.battle_guild.invites():
            await invites.delete(reason="Ban battle clean up")
            await asyncio.sleep(1)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully cleaned up the ban battle\nYou will be kick from the server after 10 seconds"), ephemeral=True)
        await asyncio.sleep(10)
        await interaction.user.kick(reason="Ban battle clean up")
        await self.battle_data['channel'].delete()
        self.battle_data = {}

    @staff.command(name="add", description="Add a user to the ban battle event manager")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: Interaction, member: discord.Member):
        if interaction.guild.id != self.battle_guild.id:
            return await interaction.response.send_message("You can only use this command in the ban battle server", ephemeral=True)
        role = interaction.guild.get_role(1118486572115959820)
        await member.add_roles(role)
        await interaction.response.send_message(f"Successfully added {member.mention} to the ban battle event manager", ephemeral=True)


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(1122510437011955862)
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                self.webhook = webhook
                break
        if self.webhook is None:
            avatar = await self.bot.user.avatar.read()
            self.webhook = await channel.create_webhook(name=f"{self.bot.user.name} Message Logger", avatar=avatar)            

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None: return
        if message.guild.id != 785839283847954433: return

        embeds = []
        embed = discord.Embed(title="Message | Deleted", description="", color=message.author.color)
        embed.description += f"\n**Channel:** `{message.channel.name} | {message.channel.id}` {message.channel.mention}"
        embed.description += f"\n**Author:** {message.author.mention}"
        embed.description += f"\n**Message:**" + message.content if message.content is not None else "`None`"
        embed.description += f"\n**Created At:** {message.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        if message.reference is not None:
            try:
                ref_message = await message.channel.fetch_message(message.reference.message_id)
                embed.description += f"\n**Replying to:** {ref_message.author.mention}"
                embed.description += f"\n**Reply Message Content:** {ref_message.content}"
            except discord.NotFound:
                pass
        embed.description += f"\n**Jump:** [Click Here]({message.jump_url})"
        if len(message.attachments) > 0:
            files = []
            for file in message.attachments:
                files.append(f"[{file.filename}]({file.url})")
            embed.description += f"\n**Attachments:** {', '.join(files)}\n"
        embed.set_author(name=message.author, icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar)
        embed.set_footer(text=f"Author ID: {message.author.id} | Message ID: {message.id}")
        embed.timestamp = datetime.datetime.utcnow()
        
        if message.author.bot:
            if message.interaction:
                embed.description += f"\n**Command:** {message.interaction.name}"
                embed.description += f"\n**Command User:** {message.interaction.user.mention}"

        embeds.append(embed)
        if len(message.embeds) > 0:
            for embed in message.embeds:
                embeds.append(embed)

        await self.webhook.send(embeds=embeds)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None: return
        if before.guild.id != 785839283847954433: return
        if before.content == after.content: return

        embeds = []
        embed = discord.Embed(title="Message | Edited", description="", color=after.author.color)
        embed.description += f"\n**Channel:** `{before.channel.name} | {before.channel.id}` {before.channel.mention}"
        embed.description += f"\n**Author:** {before.author.mention}"
        embed.description += f"\n**Before:**" + before.content if before.content is not None else "`None`"
        embed.description += f"\n**After:** {after.content if after.content is not None else '`None`'}"
        embed.description += f"\n**Created At:** {before.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        embed.description += f"\n**Jump:** {before.jump_url}"
        if len(before.attachments) > 0:
            files = []
            for file in before.attachments:
                files.append(f"[{file.filename}]({file.url})")
            embed.description += f"\n**Attachments:** {', '.join(files)}"
        embed.set_author(name=before.author, icon_url=before.author.avatar.url if before.author.avatar else before.author.default_avatar)
        embed.set_footer(text=f"Author ID: {before.author.id} | Message ID: {before.id}")
        embed.timestamp = datetime.datetime.utcnow()
        
        if before.author.bot:
            if before.interaction:
                embed.description += f"\n**Command:** {before.interaction.name}"
                embed.description += f"\n**Command User:** {before.interaction.user.mention}"

        embeds.append(embed)
        if len(before.embeds) > 0:
            for embed in before.embeds:
                embed = discord.Embed.from_dict(embed.to_dict())
                if embed.title:
                    embed.title += "| Before Edit"
                else:
                    embed.title = "| Before Edit"
                embeds.append(embed)
        if len(after.embeds) > 0:
            for embed in after.embeds:
                embed = discord.Embed.from_dict(embed.to_dict())
                if embed.title:
                    embed.title += "| After Edit"
                else:
                    embed.title = "| After Edit"
                embeds.append(embed)

        await self.webhook.send(embeds=embeds)  
    
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        message = discord.Message(state=self.bot._connection, channel=self.bot.get_channel(payload.channel_id), data=payload.data)
        if message.guild is None: return
        if message.author.id != 1103919979809734787: return
        if message.channel.id != 1103892836564357180: return
        gc = self.bot.get_channel(785847439579676672)

        if "**Ready to be watered!**" in message.embeds[0].description:            
            await gc.send(f"Hey fellow tree lovers!, Server tree is ready to be watered! {message.jump_url}", delete_after=10)
            return
        
        view = discord.ui.View.from_message(message)
        if len(view.children) == 3:
            await gc.send(f"Hey fellow tree lovers!, there is a bug on the tree catch it before it's gone! {message.jump_url}", delete_after=10)
            return


class karuta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='karuta-access', aliases=['ka'])
    async def karuta_access(self, ctx):
        if not ctx.guild: return
        if ctx.author.guild.id != 785839283847954433: return
        blacklist_role = ctx.guild.get_role(1121782006628503683)
        access_role = ctx.guild.get_role(1034072149247397938)
        if blacklist_role in ctx.author.roles:
            await ctx.author.remove_roles(access_role)
            return await ctx.send("You are blacklisted from using this command!")
        level_role = ctx.guild.get_role(811307879318945872)
        donor_role = ctx.guild.get_role(810128688267919381)
        if level_role or donor_role in ctx.author.roles:
            if access_role in ctx.author.roles:
                await ctx.author.remove_roles(access_role)
                return await ctx.send("Your access to the karuta has been revoked!")
            await ctx.author.add_roles(access_role)
            return await ctx.send("You now have access to the karuta commands!")
        else:
            await ctx.send("You need to be level 10 or a donor to use this command!")
    
    @commands.command(name="karuta-bl")
    @commands.has_permissions(ban_members=True)
    async def karuta_bl(self, ctx, user:discord.Member):
        if not ctx.guild: return
        if ctx.author.guild.id != 785839283847954433: return
        blacklist_role = ctx.guild.get_role(1121782006628503683)
        access_role = ctx.guild.get_role(1034072149247397938)
        if blacklist_role in user.roles:
            await user.remove_roles(access_role)
            await user.add_roles(blacklist_role)
            await ctx.send("User is already blacklisted")
        else:
            await user.add_roles(blacklist_role)
            await user.remove_roles(access_role)
            await ctx.send("User has been blacklisted")        
                
async def setup(bot):
    await bot.add_cog(Basic(bot), guilds=[discord.Object(785839283847954433)])
    await bot.add_cog(Afk(bot), guilds=[discord.Object(785839283847954433)])
    await bot.add_cog(Appeal_server(bot), guilds=[discord.Object(988761284956799038)])
    await bot.add_cog(karuta(bot))
    await bot.add_cog(Logging(bot))






        
    

