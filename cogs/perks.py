import discord
import datetime
import humanfriendly
import aiohttp
import re
from discord import Interaction, app_commands
from discord.app_commands import Group
from discord.ext import commands, tasks
from utils.db import Document
from typing import Literal, Union
from utils.transformer import MutipleChannel, TimeConverter
from utils.paginator import Paginator
from utils.views.buttons import Link_view, Confirm


class Perks_DB:
    def __init__(self, bot, Document):
        self.bot = bot
        self.db = self.bot.mongo["perks_db"]
        self.roles = Document(self.db, "custom_roles")
        self.channel = Document(self.db, "custom_channel")
        self.react = Document(self.db, "custom_react")
        self.highlight = Document(self.db, "custom_highlight")
        self.config = Document(self.db, "custom_perks_config")        
        self.cach = {'react': {}, 'highlight': {}}
    
    async def get_data(self, db, guild_id, user_id):
        match db:
            case "roles":
                return await self.roles.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
            case "channel":
                return await self.channel.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
            case "react":
                return await self.react.find_by_custom({'guild_id': guild_id, 'user_id': user_id, 'last_react': None})
            case "highlight":
                return await self.highlight.find_by_custom({'guild_id': guild_id, 'user_id': user_id, 'last_trigger': None})
            case 'config':
                return await self.config.find(guild_id)
            case 'all':
                role_data = await self.roles.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
                channel_data = await self.channel.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
                react_data = await self.react.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
                highlight_data = await self.highlight.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
                data = {}
                if role_data: data['role'] = role_data
                if channel_data: data['channel'] = channel_data
                if react_data: data['react'] = react_data
                if highlight_data: data['highlight'] = highlight_data                
                return data
    
    async def update(self, type: str, data:dict):
        match type:
            case "roles":
                await self.roles.update(data['_id'], data)
            case "channel":
                await self.channel.update(data['_id'], data)
            case "react":
                await self.react.update(data['_id'], data)
            case "highlight":
                await self.highlight.update(data['_id'], data)
            case 'config':
                await self.config.update(data['_id'], data)

    async def delete(self, type: str,data: dict):
        match type:
            case "roles":
                await self.roles.delete(data['_id'])
            case "channel":
                await self.channel.delete(data['_id'])
            case "react":
                await self.react.delete(data['_id'])
            case "highlight":
                await self.highlight.delete(data['_id'])
            case 'config':
                await self.config.delete(data['_id'])


    async def create(self, type: str, user_id: int, guild_id: int, duration: Union[int, str], friend_limit: int=None):
        match type:
            case "roles":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'role_id': None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': []}
                await self.roles.insert(perk_data)
                return perk_data
            case "channel":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'channel_id':None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': []}
                await self.channel.insert(perk_data)
                return perk_data
            case "react":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'emoji': None, 'last_react': None}
                await self.react.insert(perk_data)
                return perk_data

            case "highlight":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'triggers': [], 'ignore_channel':[], 'ignore_users': [], 'last_trigger': None}
                await self.highlight.insert(perk_data)
                return perk_data
            case 'config':
                perk_config = {'_id': guild_id,'custom_category': None,'custom_roles_position': 0}
                await self.config.insert(perk_config)
                return perk_config
            case _:
                raise Exception("Invalid perk type")
    
    async def create_cach(self):
        for data in await self.react.get_all():
            if 'guild_id' not in self.cach['react'].keys():
                self.cach['react'][data['guild_id']] = {}
            
            if 'user_id' not in self.cach['react'][data['guild_id']].keys():
                self.cach['react'][data['guild_id']][data['user_id']] = data
        
        for data in await self.highlight.get_all():
            if 'guild_id' not in self.cach['highlight'].keys():
                self.cach['highlight'][data['guild_id']] = {}
            
            if 'user_id' not in self.cach['highlight'][data['guild_id']].keys():
                self.cach['highlight'][data['guild_id']][data['user_id']] = data
        
        print(self.cach['highlight'])
    
    async def update_cache(self, perk:str,user_id: int, guild_id: int, data):
        match perk:
            case "react":
                if 'guild_id' not in self.cach['react'].keys():
                    self.cach['react'][guild_id] = {}
                if 'user_id' not in self.cach['react'][guild_id].keys():
                    self.cach['react'][guild_id][user_id] = {}
                self.cach['react'][guild_id][user_id] = data
            case "highlight":
                if 'guild_id' not in self.cach['highlight'].keys():
                    self.cach['highlight'][guild_id] = {}
                if 'user_id' not in self.cach['highlight'][guild_id].keys():
                    self.cach['highlight'][guild_id][user_id] = {}
                self.cach['highlight'][guild_id][user_id] = data
            case _:
                raise Exception("Invalid perk type")

@app_commands.guild_only()
class Perks(commands.GroupCog, name="perks", description="manage your custom perks"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.perk: Perks_DB = Perks_DB(bot, Document)
    
    edit = Group(name="edit", description="edit your perks")
    create = Group(name="create", description="create your perks")
    highlight = Group(name="highlight", description="manage your highlight perks")
    friend = Group(name="friend", description="give/revoke your custom role/channel access from your friends")
    delete = Group(name="delete", description="delete your perks temporarily")

    @app_commands.command(name="list", description="list your perks")
    async def _list(self, interaction: Interaction):
        user_data = await self.bot.perk.get_data('all', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        pages = []
        for perk, data in user_data.items():
            embed = discord.Embed(title=f"{perk.capitalize()} perks", color=0x363940, description="")
            if perk == 'role':
                embed.description += f"**Role:** <@&{data['role_id']}>"
                embed.description += f"\n**Duration:** {humanfriendly.format_timespan(data['duration']) if data['duration'] != 'permanent' else 'Permanent'}\n**Friend limit:** {data['friend_limit']}"
                embed.description += f"\nFriend list: {', '.join([f'<@{user}>' for user in data['friend_list']]) if len(data['friend_list']) > 0 else '`None`'}"
            elif perk == 'channel':
                embed.description += f"Channel: <#{data['channel_id']}>\nDuration: {data['duration']}\nFriend limit: {data['friend_limit']}"
                embed.description += f"\nFriend list: {', '.join([f'<@{user}>' for user in data['friend_list']])}"
            elif perk == 'react':
                embed.description += f"Emoji: {data['emoji']}"
            elif perk == 'highlight':
                embed.description += f"Triggers: {', '.join(data['triggers']) if data['triggers'] else '`None`'}"
                embed.description += f"\nIgnore channel: {', '.join([f'<#{channel}>' for channel in data['ignore_channel']]) if data['ignore_channel'] else '`None`'}"
                embed.description += f"\nIgnore users: {', '.join([f'<@{user}>' for user in data['ignore_users']]) if data['ignore_users'] else '`None`'}"
            pages.append(embed)

        await Paginator(interaction=interaction, pages=pages).start(embeded=True, quick_navigation=False)

    @friend.command(name="add", description="add a friend to your perks")
    @app_commands.describe(member="your friend", perk="the perk you want to give to your friend")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom Channel", value="channels")])
    async def _add(self, interaction: Interaction, member: discord.Member, perk: app_commands.Choice[str]):
        user_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        if member.id in user_data['friend_list']: return await interaction.response.send_message("This user is already in your friend list.", ephemeral=True)
        if len(user_data['friend_list']) >= user_data['friend_limit']: return await interaction.response.send_message("You have reached your friend limit.", ephemeral=True)
        user_data['friend_list'].append(member.id)
        await self.bot.perk.update(perk.value, user_data)
        role = discord.utils.get(interaction.guild.roles, id=user_data['role_id'])
        await member.add_roles(role)
        await interaction.response.send_message(embed=discord.Embed(description=f"Added {member.mention} to your friend list.", color=0x363940))
    
    @friend.command(name="remove", description="remove a friend from your perks")
    @app_commands.describe(member="your friend", perk="the perk you want to remove from your friend")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom Channel", value="channels")])
    async def _remove(self, interaction: Interaction, member: discord.Member, perk: app_commands.Choice[str]):
        user_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        if member.id not in user_data['friend_list']: return await interaction.response.send_message("This user is not in your friend list.", ephemeral=True)
        user_data['friend_list'].remove(member.id)
        await self.bot.perk.update(perk.value, user_data)
        role = discord.utils.get(interaction.guild.roles, id=user_data['role_id'])
        await member.remove_roles(role)
        await interaction.response.send_message(embed=discord.Embed(description=f"Removed {member.mention} from your friend list.", color=0x363940))

    @friend.command(name="list", description="list your friends")
    @app_commands.describe(perk="the perk you want to list your friends")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom Channel", value="channels")])
    async def _list(self, interaction: Interaction, perk: Literal['Custom Role', 'Custom Channel']):
        user_data = await self.bot.perk.get_data(perk.lower(), interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        if len(user_data['friend_list']) == 0: return await interaction.response.send_message("You don't have any friends. sed", ephemeral=True)
        embed = discord.Embed(description=f"Your friends: {', '.join([f'<@{user}>' for user in user_data['friend_list']])}", color=0x363940)
        await interaction.response.send_message(embed=embed)

    @friend.command(name="fix", description="fix your custom role friend list")
    async def _fix(self, interaction: Interaction):
        user_data = await self.bot.perk.get_data('roles', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom role. perk.", ephemeral=True)
        
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description="Are you sure you want to fix your custom role friend list?\nThis will remove all your friends from your custom role.", color=0x363940), view=view)
        await view.wait()
        if view.value:
            await view.interaction.response.edit_message(embed=discord.Embed(description="Fixing your custom role friend list...", color=0x363940), view=None)
            role = discord.utils.get(interaction.guild.roles, id=user_data['role_id'])
            for member in role.members: 
                if member.id != interaction.user.id: await member.remove_roles(role)
            user_data['friend_list'] = []
            await self.bot.perk.update_data('roles', interaction.guild.id, interaction.user.id, user_data)
            await view.interaction.edit_original_response(embed=discord.Embed(description="Fixed your custom role friend list.", color=0x363940), view=None)            

    @create.command(name="role", description="create a custom role")
    @app_commands.describe(name="name of the role", color="Hex color of the role", icon="Icon of the role")
    async def _role(self, interaction: Interaction, name: str, color: str, icon:discord.Attachment=None):
        user_data = await self.bot.perk.get_data('roles', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom role. perk.", ephemeral=True)
        if user_data['role_id'] != None: return await interaction.response.send_message("You already have a custom role.", ephemeral=True)
        perks_config = await self.bot.perk.config.find(interaction.guild.id)
        if not perks_config: return await interaction.response.send_message("This server doesn't have any perks config.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Creating your custom role...", color=0x363940))
        if icon:
            if not icon.filename.endswith(('png', 'jpg')): return await interaction.edit_original_response(embed=discord.Embed(description="Invalid icon file type.", color=0x363940))
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status != 200: return await interaction.edit_original_response(embed=discord.Embed(description="Invalid icon file type.", color=0x363940))
                    image = await resp.read()
        
        role = await interaction.guild.create_role(name=name, color=discord.Color(int(color.replace('#', ''), 16)), reason=f"Custom role for {interaction.user.display_name}", display_icon=icon)
        await role.edit(position=perks_config['custom_roles_position'])
        await interaction.user.add_roles(role, reason=f"Custom role for {interaction.user.display_name}")
        user_data['role_id'] = role.id
        await self.bot.perk.update('roles', user_data)
        await interaction.edit_original_response(embed=discord.Embed(description="Your custom role has been created.", color=0x363940))
    
    @create.command(name="channel", description="create a custom channel")
    @app_commands.describe(name="name of the channel")
    async def _channel(self, interaction: Interaction, name: str):
        user_data = await self.bot.perk.get_data('channel', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom channel. perk.", ephemeral=True)
        if user_data['channel_id'] != None: return await interaction.response.send_message("You already have a custom channel.", ephemeral=True)
        perks_config = await self.bot.perk.config.find(interaction.guild.id)
        if not perks_config: return await interaction.response.send_message("This server doesn't have any perks config.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Creating your custom channel...", color=0x363940))
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }
        if perks_config['custom_category'] == None: return await interaction.edit_original_response(embed=discord.Embed(description="This server doesn't have a custom channel category.", color=0x363940))
        channel = await interaction.guild.create_text_channel(name=name, overwrites=overwrites, reason=f"Custom channel for {interaction.user.display_name}", category=interaction.guild.get_channel(perks_config['custom_category']))
        user_data['channel_id'] = channel.id
        await self.bot.perk.update('channel', user_data)
        await interaction.edit_original_response(embed=discord.Embed(description="Your custom channel has been created.", color=0x363940))
        await channel.send(f"Welcome to your custom channel, {interaction.user.mention}!")
    
    @delete.command(name="role", description="delete your custom role")
    async def _role(self, interaction: Interaction):
        user_data = await self.bot.perk.get_data('roles', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom role. perk.", ephemeral=True)
        if user_data['role_id'] == None: return await interaction.response.send_message("You havent created a custom role yet.", ephemeral=True)
        view = Confirm(interaction.user, 30) 
        await interaction.response.send_message(embed=discord.Embed(description="Are you sure you want to delete your custom role?", color=0x363940), view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            role = interaction.guild.get_role(user_data['role_id'])
            if not role: return await interaction.edit_original_response(embed=discord.Embed(description="Your custom role is invalid/missing.", color=0x363940))
            total_seconds = (datetime.datetime.utcnow() - datetime.datetime(role.created_at.year, role.created_at.month, role.created_at.day, role.created_at.hour, role.created_at.minute, role.created_at.second)).total_seconds()            
            await role.delete(reason=f"Custom role deleted with request from role owner {interaction.user.display_name}")
            user_data['duration'] = round(user_data['duration'] - total_seconds)
            user_data['role_id'] = None
            await self.bot.perk.update('roles', user_data)
            await view.interaction.response.send_message(embed=discord.Embed(description="Your custom role has been deleted.", color=0x363940))
        else:
            for child in view.children:child.disabled = True
            await interaction.edit_original_response(embed=discord.Embed(description="Cancelled.", color=0x363940), view=view)
    
    @delete.command(name="channel", description="delete your custom channel")
    async def _channel(self, interaction: Interaction):
        user_data = await self.bot.perk.get_data('channel', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom channel. perk.", ephemeral=True)
        if user_data['channel_id'] == None: return await interaction.response.send_message("You havent created a custom channel yet.", ephemeral=True)
        view = Confirm(interaction.user, 30) 
        await interaction.response.send_message(embed=discord.Embed(description="Are you sure you want to delete your custom channel?", color=0x363940), view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            channel = interaction.guild.get_channel(user_data['channel_id'])
            if not channel: return await interaction.edit_original_response(embed=discord.Embed(description="Your custom channel is invalid/missing.", color=0x363940))
            total_seconds = (datetime.datetime.utcnow() - datetime.datetime(channel.created_at.year, channel.created_at.month, channel.created_at.day, channel.created_at.hour, channel.created_at.minute, channel.created_at.second)).total_seconds()
            await channel.delete(reason=f"Custom channel deleted with request from channel owner {interaction.user.display_name}")
            user_data['duration'] = round(user_data['duration'] - total_seconds)
            user_data['channel_id'] = None
            await self.bot.perk.update('channel', user_data)
            await view.interaction.response.edit_message(embed=discord.Embed(description="Your custom channel has been deleted.", color=0x363940), view=None)
        else:
            for child in view.children:child.disabled = True
            await interaction.edit_original_response(embed=discord.Embed(description="Cancelled.", color=0x363940), view=view)

    @edit.command(name="role", description="edit your role perk")
    async def edit_role(self, interaction: Interaction, name: str=None, color:str=None, icon: discord.Attachment=None):
        perk_data = await self.bot.perk.get_data('roles', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any role perks yet.", ephemeral=True)
        role = interaction.guild.get_role(perk_data['role_id'])
        if not role: return await interaction.response.send_message("Your role perk is invalid/missing.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we edit your role perk", color=0x363940))
        if icon:
            if not icon.filename.url.endswith(('png', 'jpg')): return await interaction.edit_original_response(embed=discord.Embed(description="Invalid image type.", color=0x363940))
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status != 200: return await interaction.edit_original_response(embed=discord.Embed(description="Invalid image url.", color=0x363940))
                    image = await resp.read()
                    
        await role.edit(name=name, color=int(color.replace("#", ""), 16) if color else None, icon=image if icon else None)
        await interaction.edit_original_response(embed=discord.Embed(description="Your Custom Role as been edited.", color=0x363940))
    
    @edit.command(name="channel", description="edit your channel perk")
    async def edit_channel(self, interaction: Interaction, name: str=None, topic: str=None):
        perk_data = await self.bot.perk.get_data('channel', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any channel perks yet.", ephemeral=True)
        channel = interaction.guild.get_channel(perk_data['channel_id'])
        if not channel: return await interaction.response.send_message("Your channel perk is invalid/missing.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we edit your channel perk", color=0x363940))
        await channel.edit(name=name, topic=topic)
        await interaction.edit_original_response(embed=discord.Embed(description="Your Custom Channel as been edited.", color=0x363940))
    
    @edit.command(name="react", description="edit your react perk")
    async def edit_react(self, interaction: Interaction, emoji: str):
        perk_data = await self.bot.perk.get_data('react', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any react perks yet.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we check your emoji", color=0x363940))
        message = await interaction.original_response()
        try:
            await message.add_reaction(emoji)
            await message.remove_reaction(emoji, self.bot.user)
        except:
            return await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji.", color=0x363940))
        perk_data['emoji'] = emoji
        await self.bot.perk.update('react', perk_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Your Custom React as been set to {emoji}", color=0x363940))
        await self.bot.perk.update_cache('react', interaction.user.id, interaction.guild.id, perk_data)

    @highlight.command(name="add", description="add a highlight")
    @app_commands.describe(trigger="The trigger for the highlight")
    async def highlight_add(self, interaction: Interaction, trigger: str):
        perk_data = await self.bot.perk.get_data('highlight', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any highlight perks yet.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we add your highlight", color=0x363940))
        perk_data['triggers'].append(trigger)
        await self.bot.perk.update('highlight', perk_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"`{trigger} has been added to your highlights.", color=0x363940))
        await self.bot.perk.update_cache('highlight', interaction.user.id, interaction.guild.id, perk_data)
    
    @highlight.command(name="remove", description="remove a highlight")
    @app_commands.describe(trigger="The trigger for the highlight")
    async def highlight_remove(self, interaction: Interaction, trigger: str):
        perk_data = await self.bot.perk.get_data('highlight', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any highlight perks yet.", ephemeral=True)
        if trigger not in perk_data['triggers']: return await interaction.response.send_message("That trigger doesn't exist.", ephemeral=True)
        perk_data['triggers'].remove(trigger)
        await self.bot.perk.update('highlight', perk_data)
        await interaction.response.send_message("Your Highlight as been removed.", ephemeral=True)
        await self.bot.perk.update_cache('highlight', interaction.user.id, interaction.guild.id, perk_data)
    
    @highlight.command(name="channel", description="manage your ignore/unignore channels")
    async def highlight_channel(self, interaction: Interaction, option: Literal['ignore', 'unignore'], channel: app_commands.Transform[discord.TextChannel, MutipleChannel]):
        perks_data = await self.bot.perk.get_data('highlight', interaction.guild.id, interaction.user.id)
        if not perks_data: return await interaction.response.send_message("You don't have any highlight perks yet.", ephemeral=True)
        embed = discord.Embed(description=f"New {option} channels:")
        if option == 'ignore':
            for channel in channel:
                if channel.id not in perks_data['ignore_channel']:
                    perks_data['ignore_channel'].append(channel.id)
                    embed.description += f"`-`{channel.mention}\n"
        else:
            for channel in channel:
                if channel.id in perks_data['ignore_channel']:
                    perks_data['ignore_channel'].remove(channel.id)
                    embed.description += f"`-`{channel.mention}\n"
        embed.description += "If any of these channels are not in the list, it means they are already in the list."
        await interaction.response.send_message(embed=embed)
        await self.bot.perk.update('highlight', perks_data)
        await self.bot.perk.update_cache('highlight', interaction.user.id, interaction.guild.id, perks_data)
    
class Perk_BackEND(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_perk_task_role = self.check_perk_expire_role.start()
        self.react_perk_channel = self.check_perk_expire_channel.start()
        self.role_task_in_progress = False
        self.channel_task_in_progress = False
    
    def cog_unload(self):
        self.role_perk_task_role.cancel()
        self.react_perk_channel.cancel()

    
    async def autoreact(self, message):
        if message.author.bot: return
        if message.guild is None: return
        if message.guild.id not in self.bot.perk.cach['react'].keys(): return

        for mention in message.mentions:
            if mention.id not in self.bot.perk.cach['react'][message.guild.id].keys(): continue
            user_data = self.bot.perk.cach['react'][message.guild.id][mention.id]
            if user_data['last_react'] is None or (datetime.datetime.utcnow() - user_data['last_react']).total_seconds() > 60:
                try:
                    await message.add_reaction(user_data['emoji'])
                except:
                    return
                user_data['last_react'] = datetime.datetime.utcnow()
                await self.bot.perk.update_cache('react', mention.id, message.guild.id, user_data)
                await self.bot.perk.update('react', user_data)
    
    async def highlight(self, message):
        if message.author.bot: return
        if message.guild is None: return
        if message.guild.id not in self.bot.perk.cach['highlight'].keys(): return

        message_content = message.content.lower().split()
        guild_data = self.bot.perk.cach['highlight'][message.guild.id]
        for user_id, user_data in guild_data.items():
            if user_id == message.author.id: continue
            for trigger in user_data['triggers']:
                if message.channel.id in user_data['ignore_channel']: continue
                if message.author.id in user_data['ignore_channel']: continue

                for trigger in message_content:
                    if trigger in user_data['triggers']:
                        if user_data['last_trigger'] is None or (datetime.datetime.utcnow() - user_data['last_trigger']).total_seconds() > 300:
                            self.bot.dispatch('highlight', message, user_id, user_data)
                            user_data['last_trigger'] = datetime.datetime.utcnow()
                        else:
                            continue
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.perk.create_cach()
    
    @tasks.loop(seconds=10)
    async def check_perk_expire_role(self):
        if self.role_task_in_progress: return
        self.role_task_in_progress = True
        data = await self.bot.perk.roles.get_all()
        now = datetime.datetime.utcnow()
        for perks in data:
            guild = self.bot.get_guild(perks['guild_id'])
            user = guild.get_member(perks['user_id'])
            if not user:
                role = guild.get_role(perks['role_id'])
                if role: await role.delete(reason="User left the server/not found")
                await self.bot.perk.delete('role', perks)
            if perks['duration'] == 'permanent': continue
            if perks['role_id'] is None: continue
            role = guild.get_role(perks['role_id'])
            if not role: continue
            role_created_at = datetime.datetime.utcfromtimestamp(role.created_at.timestamp())
            if now > role_created_at + datetime.timedelta(seconds=perks['duration']):
                await role.delete(reason="Custom role expired")
                await self.bot.perk.delete('role', perks)
                try:
                    await user.send(f"Your custom role in {guild.name} has expired and has been removed.")
                except:
                    pass
        self.role_task_in_progress = False
    
    @tasks.loop(seconds=10)
    async def check_perk_expire_channel(self):
        if self.channel_task_in_progress: return
        self.channel_task_in_progress = True
        data = await self.bot.perk.channel.get_all()
        now = discord.utils.utcnow()
        for perks in data:
            guild = self.bot.get_guild(perks['guild_id'])
            user = guild.get_member(perks['user_id'])
            if not user:
                channel = guild.get_channel(perks['channel_id'])
                if channel: await channel.delete(reason="User left the server/not found")
                await self.bot.perk.delete('channel', perks)
            if perks['duration'] == 'permanent': continue
            if perks['channel_id'] is None: continue
            channel = guild.get_channel(perks['channel_id'])
            if not channel: continue
            channel_created_at = channel.created_at
            if now > channel_created_at + datetime.timedelta(seconds=perks['duration']):
                await channel.delete(reason="Custom channel expired")
                await self.bot.perk.delete('channel', perks)
                try:
                    await user.send(f"Your custom channel in {guild.name} has expired and has been removed.")
                except:
                    pass
        self.channel_task_in_progress = False
    
    @check_perk_expire_channel.before_loop
    async def before_check_perk_expire_channel(self):
        await self.bot.wait_until_ready()
    
    @check_perk_expire_role.before_loop
    async def before_check_perk_expire_role(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_highlight(self, message: discord.Message, user_id: int,user_data: dict):
        messages = []
        async for msg in message.channel.history(limit=20, before=message):
            if msg.author.id == user_id:
                if not (msg.created_at - message.created_at).total_seconds() > 300:
                    return
            messages.append(msg)

        embed = discord.Embed(description="", color=0x363940)
        messages.reverse()
        for msg in messages[:4]:
            embed.description += f"**[{msg.created_at.strftime('%H:%M:%S')}] {msg.author.name}:** {msg.content}\n"
        
        embed.description += f"**[{message.created_at.strftime('%H:%M:%S')}] {message.author.name}:** {message.content}"
        user = message.guild.get_member(user_id)
        if user is None: return
        try:
            view = Link_view("Jump to message", message.jump_url)
            await user.send(embed=embed, view=view)
        except Exception as e:
            print(e)
        user_data['last_trigger'] = datetime.datetime.utcnow()
        await self.bot.perk.update_cache('highlight', user_id, message.guild.id, user_data)
        await self.bot.perk.update('highlight', user_data)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.guild is None: return
        if len(message.mentions) > 0: await self.autoreact(message)
        await self.highlight(message)

@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class Perk_Config(commands.GroupCog, name="perk", description="Configure your perks"):
    def __init__(self, bot):
        self.bot = bot
    
    config = Group(name="config", description="Configure your perks")

    @config.command(name="channel-category", description="Set the category for your custom channels")
    @app_commands.describe(category="The category you want to set")
    async def channel_category(self, interaction: Interaction, category: discord.CategoryChannel):
        perk_data = await self.bot.perk.get_data('config', interaction.guild.id, interaction.user.id)
        if perk_data is None: 
            perk_data = {'_id': interaction.guild.id, 'custom_category': None, 'custom_roles_position': 0}
            await self.bot.perk.config.insert(perk_data)
        perk_data['custom_category'] = category.id
        await self.bot.perk.update('config', perk_data)
        await interaction.response.send_message(embed=discord.Embed(description=f"Your custom channel category has been set to {category.mention}", color=0x363940))
    
    @config.command(name="role-position", description="Set the position for your custom roles")
    @app_commands.describe(position="The position you want to set")
    async def role_position(self, interaction: Interaction, position: int):
        perk_data = await self.bot.perk.get_data('config', interaction.guild.id, interaction.user.id)
        if perk_data is None: 
            perk_data = {'_id': interaction.guild.id, 'custom_category': None, 'custom_roles_position': 0}
            await self.bot.perk.config.insert(perk_data)
        perk_data['custom_roles_position'] = position
        await self.bot.perk.update('config', perk_data)
        await interaction.response.send_message(embed=discord.Embed(description=f"Your custom role position has been set to {position}", color=0x363940))
    
    @config.command(name="show", description="Show your perk config")
    async def show(self, interaction: Interaction):
        perk_data = await self.bot.perk.get_data('config', interaction.guild.id, interaction.user.id)
        if perk_data is None: 
            perk_data = {'_id': interaction.guild.id, 'custom_category': None, 'custom_roles_position': 0}
            await self.bot.perk.config.insert(perk_data)
        embed = discord.Embed(color=0x363940, description="")
        embed.description += f"**Custom Channel Category:** {interaction.guild.get_channel(perk_data['custom_category']).mention if interaction.guild.get_channel(perk_data['custom_category']) is not None else 'None'}\n"
        embed.description += f"**Custom Role Position:** {perk_data['custom_roles_position'] if perk_data['custom_roles_position'] is not None else 'None'}\n"
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove", description="Remove perks from your server members")
    @app_commands.describe(perk="The perk you want to remove", member="The member you want to remove the perk from")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Channel", value="channel"), app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom React", value="react"), app_commands.Choice(name="Highlight", value="highlight")])
    async def perk(self, interaction: Interaction, perk: app_commands.Choice[str], member: discord.Member):
        user_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
        if user_data is None: return await interaction.response.send_message(embed=discord.Embed(description=f"{member.mention} doesn't have the {perk.name} perk", color=0x363940))

        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description=f"Are you sure you want to remove the {perk.name} perk from {member.mention}?", color=0x363940), view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value is None or False: return await view.message.edit(embed=discord.Embed(description=f"Timed out/Cancelled", color=0x363940), view=None)
        await view.interaction.response.edit_message(embed=discord.Embed(description="Please wait while i remove the perk..."), color=0x363940, view=None)
        match perk.value:
            case "role":
                role = interaction.guild.get_role(user_data['role_id'])
                if role is not None: await role.delete(reason=f"Perk Remvoed by {interaction.user.name}")
                await self.bot.perk.delete(user_data)
            case "channel":
                channel = interaction.guild.get_channel(user_data['channel_id'])
                if channel is not None: await channel.delete(reason=f"Perk Remvoed by {interaction.user.name}")
                await self.bot.perk.delete(user_data)
            case "react":
                await self.bot.perk.delete(user_data)
                try:await self.bot.perk.cache['react'].pop(user_data['user_id'])
                except KeyError:pass
            case "highlight":
                await self.bot.perk.delete(user_data)
                try:await self.bot.perk.cache['highlight'].pop(user_data['user_id'])
                except KeyError:pass
        
    
    @app_commands.command(name="give", description="Give perks to your server members")
    @app_commands.describe(perk="The perk you want to give", member="The member you want to give the perk to")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Channel", value="channel"), app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom React", value="react"), app_commands.Choice(name="Highlight", value="highlight")])
    async def perk(self, interaction: Interaction, perk: app_commands.Choice[str], member: discord.Member, duration: app_commands.Transform[int, TimeConverter]="permanent", friend_limit: app_commands.Range[int, 1, 10]=5):
        if member.bot: return await interaction.response.send_message("You can't give perks to bots.", ephemeral=True)
        perk_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, member.id)
        if perk_data: return await interaction.response.send_message("This member already has this perk.", ephemeral=True)
        perk_data = await self.bot.perk.create(perk.value, member.id, interaction.guild.id, duration, friend_limit)
        await interaction.response.send_message(f"Perk `{perk.value}` has been given to {member.mention}.", ephemeral=True)
        await interaction.channel.send(f"{member.mention} Now you have the perk `{perk.value}`. You can use it by typing `/perk {perk.value}`")

async def setup(bot):
    await bot.add_cog(Perks(bot))
    await bot.add_cog(Perk_Config(bot))
    await bot.add_cog(Perk_BackEND(bot))

