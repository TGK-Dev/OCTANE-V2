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
        self.db = self.bot.mongo["Perk_Database"]
        self.roles = Document(self.db, "custom_roles")
        self.channel = Document(self.db, "custom_channel")
        self.react = Document(self.db, "custom_react")
        self.highlight = Document(self.db, "custom_highlight")
        self.config = Document(self.db, "config")        
        self.cach = {'react': {}, 'highlight': {}}
    
    async def get_data(self, db, guild_id, user_id):
        match db:
            case "roles":
                return await self.roles.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
            case "channel":
                return await self.channel.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
            case "react":
                return await self.react.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
            case "highlight":
                return await self.highlight.find_by_custom({'guild_id': guild_id, 'user_id': user_id})
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
        self.cach = {'react': {}, 'highlight': {}}
        config = await self.config.get_all()
        for guild in config:
            if guild['_id'] not in self.cach['react'].keys():
                self.cach['react'][guild['_id']] = {}
            if guild['_id'] not in self.cach['highlight'].keys():
                self.cach['highlight'][guild['_id']] = {}
        
        react = await self.react.get_all()
        for data in react:
            if data['emoji'] != None:
                self.cach['react'][data['guild_id']][data['user_id']] = data
        
        highlight = await self.highlight.get_all()
        for data in highlight:
            if data['guild_id'] not in self.cach['highlight'].keys():
                self.cach['highlight'][data['guild_id']]['user_id'] = data

    async def update_cache(self, perk:str,user_id: int, guild_id: int, data):
        match perk:
            case "react":
                self.cach['react'][guild_id][user_id] = data
                return
            case "highlight":
                self.cach['highlight'][guild_id][user_id] = data
                return
            case _:
                raise Exception("Invalid perk type")

@app_commands.guild_only()
class Perks(commands.GroupCog, name="perks", description="manage your custom perks"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.perk: Perks_DB = Perks_DB(bot, Document)
    
    edit = Group(name="edit", description="edit your perks")
    highlight = Group(name="highlight", description="manage your highlight perks")
    friend = Group(name="friend", description="give/revoke your custom role/channel access from your friends")
    delete = Group(name="delete", description="delete your perks temporarily")

    @app_commands.command(name="list", description="list your perks")
    async def _list(self, interaction: Interaction):
        user_data = await self.bot.perk.get_data('all', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        pages = []
        for perk, data in user_data.items():
            embed = discord.Embed(title=f"{perk.capitalize()} perks", color=0x2b2d31, description="")
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
    
    @app_commands.command(name="claim", description="claim your perks")
    @app_commands.describe(perk="the perk you want to claim", name="the name of your custom role", color="the color of your custom role", icon="the icon of your custom role", emoji="the emoji of your reaction")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Role", value="roles"),app_commands.Choice(name="Custom Channel", value="channel"),app_commands.Choice(name="Custom Reaction (ar)", value="react")])
    async def _claim(self, interaction: Interaction, perk: app_commands.Choice[str], name:str=None, color:str=None, icon: discord.Attachment=None, emoji:str=None):
        user_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message(f"You don't have any `{perk.value}` perks.", ephemeral=True)

        match perk.value:
            case "roles":
                if user_data['role_id'] != None: return await interaction.response.send_message("you already have created a custom role.", ephemeral=True)
                perks_config = await self.bot.perk.config.find(interaction.guild.id)
                if not perks_config: return await interaction.response.send_message("This server doesn't have any perks.", ephemeral=True)

                await interaction.response.send_message(embed=discord.Embed(description="Creating your custom role...", color=0x2b2d31))
                if icon:
                    if not icon.filename.endswith(('png', 'jpg')):
                        return await interaction.edit_original_response(embed=discord.Embed(description="Invalid icon file type.", color=0x2b2d31))
                    async with aiohttp.ClientSession() as session:
                        async with session.get(icon.url) as resp:
                            if resp.status != 200:
                                return await interaction.edit_original_response(embed=discord.Embed(description="Invalid icon url.", color=0x2b2d31))
                            icon = await resp.read()
                try:
                    if color: color = discord.Color(int(color.replace("#", ""), 16))
                except:
                    await interaction.edit_original_response(embed=discord.Embed(description="Invalid color Hex code.", color=0x2b2d31))

                role = await interaction.guild.create_role(name=name, color=color, reason=f"Custom role perk for {interaction.user}", display_icon=icon)
                position_role = interaction.guild.get_role(perks_config['custom_roles_position'])
                position = position_role.position - 1
                await role.edit(position=position)
                await interaction.user.add_roles(role, reason=f"Custom role perk for {interaction.user}")
                await interaction.edit_original_response(embed=discord.Embed(description="Your custom role has been created.", color=0x2b2d31))
                user_data['role_id'] = role.id
                await self.bot.perk.update(perk.value, user_data)
            
            case "channel":
                if user_data['channel_id'] != None: return await interaction.response.send_message("You already have a channel perk.", ephemeral=True)
                perks_config = await self.bot.perk.config.find(interaction.guild.id)
                if not perks_config: return await interaction.response.send_message("This server doesn't have any perks.", ephemeral=True)

                await interaction.response.send_message(embed=discord.Embed(description="Creating your custom channel...", color=0x2b2d31))
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=True, use_external_emojis=True, use_application_commands=True, attach_files=True),
                    interaction.user: discord.PermissionOverwrite(view_channel=True),
                    interaction.guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True, manage_permissions=True, manage_webhooks=True, manage_messages=True, manage_roles=True)
                }
                channel = await interaction.guild.create_text_channel(name=name, overwrites=overwrites, reason=f"Custom channel perk for {interaction.user}", category=interaction.guild.get_channel(perks_config['custom_category'] if perks_config['custom_category'] else None))
                await interaction.edit_original_response(embed=discord.Embed(description="Your custom channel has been created.", color=0x2b2d31))
                await channel.send(f"Welcome to your custom channel, {interaction.user.mention}!")
                user_data['channel_id'] = channel.id
                await self.bot.perk.update(perk.value, user_data)
            
            case "react":
                if not emoji: return await interaction.response.send_message("You need to provide an emoji.", ephemeral=True)
                await interaction.response.send_message(embed=discord.Embed(description="Checking your emoji validity...", color=0x2b2d31))
                message = await interaction.original_response()
                try:
                    await message.add_reaction(emoji)
                except:
                    return await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji.", color=0x2b2d31))
                user_data['emoji'] = emoji
                await message.remove_reaction(emoji, self.bot.user)
                await self.bot.perk.update(perk.value, user_data)
                await self.bot.perk.update_cache(perk.value, interaction.user.id , interaction.guild.id, user_data)
                await interaction.edit_original_response(embed=discord.Embed(description="Your Custom reaction has been set.", color=0x2b2d31))

    @app_commands.command(name="friend", description="manage your friends list")
    @app_commands.describe(perk="The perk you want to manage", option="The option you want to use", traget="The user you want to add/remove from your friends list")
    @app_commands.choices(option=[app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove"), app_commands.Choice(name="List", value="list"), app_commands.Choice(name="Clear", value="clear"), app_commands.Choice(name="fix", value="fix")],perk=[app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom Channel", value="channel")])
    async def _friend(self, interaction: Interaction, perk: app_commands.Choice[str],option: app_commands.Choice[str], traget: discord.Member=None):
        user_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
        perk_config = await self.bot.perk.config.find(interaction.guild.id)

        match perk.value:

            case "roles":

                if not user_data['role_id']: return await interaction.response.send_message("You haven't created a custom role yet.", ephemeral=True)
                role = interaction.guild.get_role(user_data['role_id'])
                if not role: return await interaction.response.send_message("Your custom role has been deleted/missing.", ephemeral=True)

                if option.value == "add":
                    if len(user_data['friend_list']) >= user_data['friend_limit']: return await interaction.response.send_message(f"You have reached your friend limit ({user_data['friend_limit']}).", ephemeral=True)
                    if traget is None: return await interaction.response.send_message("You need to provide a member.", ephemeral=True)
                    if traget.id in user_data['friend_list']: return await interaction.response.send_message("This user is already in your friend list.", ephemeral=True)
                    else:
                        user_data['friend_list'].append(traget.id)
                        await traget.add_roles(role, reason=f"Custom role perk for {interaction.user}")
                        await interaction.response.send_message(embed=discord.Embed(description=f"{traget.mention} has been added to your friend list.", color=0x2b2d31))
                elif option.value == "remove":
                    if traget is None: return await interaction.response.send_message("You need to provide a member.", ephemeral=True)
                    if traget.id not in user_data['friend_list']: return await interaction.response.send_message("This user is not in your friend list.", ephemeral=True)
                    else:
                        user_data['friend_list'].remove(traget.id)
                        await traget.remove_roles(role, reason=f"Custom role perk for {interaction.user}")
                        await self.bot.perk.update(perk.value, user_data)
                        await interaction.response.send_message(embed=discord.Embed(description=f"{traget.mention} has been removed from your friend list.", color=0x2b2d31))
                elif option.value == "list":
                    embed = discord.Embed(title="Your friend list for your custom role", color=0x2b2d31, description="")
                    if len(user_data['friend_list']) == 0: embed.description = "you don't have any friends in your friend list. **;-;**"
                    else:
                        for friend in user_data['friend_list']:
                            embed.description += f"<@{friend}>\n"
                    await interaction.response.send_message(embed=embed)
                elif option.value == "clear":
                    for friend in role.members:
                        if friend.id != interaction.user.id:
                            friend.remove_roles(role, reason=f"Custom role perk for {interaction.user}")
                    user_data['friend_list'] = []
                    await self.bot.perk.update(perk.value, user_data)
                    await interaction.response.send_message(embed=discord.Embed(description="Your friend list has been cleared.", color=0x2b2d31))
                elif option.value == "fix":
                    await interaction.response.send_message(embed=discord.Embed(description="Fixing your friend list...", color=0x2b2d31))
                    for friend in role.members:
                        if friend.id not in user_data['friend_list']:
                            user_data['friend_list'].append(friend.id)
                        await self.bot.perk.update(perk.value, user_data)
                    await interaction.edit_original_response(embed=discord.Embed(description="Your friend list has been fixed.", color=0x2b2d31))
        
            case "channel":
                if not user_data['channel_id']: return await interaction.response.send_message("You haven't created a custom channel yet.", ephemeral=True)
                channel = interaction.guild.get_channel(user_data['channel_id'])
                if not channel: return await interaction.response.send_message("Your custom channel has been deleted/missing.", ephemeral=True)
                
                if option.value == "add":
                    if len(user_data['friend_list']) >= user_data['friend_limit']: return await interaction.response.send_message(f"You have reached your friend limit ({user_data['friend_limit']}).", ephemeral=True)
                    if traget.id in user_data['friend_list']: return await interaction.response.send_message("This user is already in your friend list.", ephemeral=True)
                    await channel.set_permissions(traget, view_channel=True, reason=f"Custom channel perk for {interaction.user}")
                    user_data['friend_list'].append(traget.id)
                    await self.bot.perk.update(perk.value,user_data)
                    await interaction.response.send_message(embed=discord.Embed(description=f"{traget.mention} has been added to your friend list.", color=0x2b2d31))
                    await channel.send(f"{traget.mention} you have been added to {interaction.user.mention}'s custom channel friend list.")
                elif option.value == "remove":
                    if traget.id not in user_data['friend_list']: return await interaction.response.send_message("This user is not in your friend list.", ephemeral=True)
                    await channel.set_permissions(traget, overwrite=None, reason=f"Custom channel perk for {interaction.user}")
                    user_data['friend_list'].remove(traget.id)
                    await self.bot.perk.update(perk.value,user_data)
                    await interaction.response.send_message(embed=discord.Embed(description=f"{traget.mention} has been removed from your friend list.", color=0x2b2d31))
                elif option.value == "list":
                    embed = discord.Embed(title="Your friend list for your custom channel", color=0x2b2d31, description="")
                    if len(user_data['friend_list']) == 0: embed.description = "you don't have any friends in your friend list. **;-;**"
                    else:
                        for friend in user_data['friend_list']:
                            embed.description += f"<@{friend}>\n"
                    await interaction.response.send_message(embed=embed)
                elif option.value == "clear":
                    for friend in channel.overwrites:
                        if friend.id != interaction.user.id:
                            await channel.set_permissions(friend, overwrite=None, reason=f"Custom channel perk for {interaction.user}")
                    user_data['friend_list'] = []
                    await self.bot.perk.update(perk.value,user_data)
                    await interaction.response.send_message(embed=discord.Embed(description="Your friend list has been cleared.", color=0x2b2d31))
                elif option.value == "fix":
                    for user in user_data['friend_list']:
                        user = interaction.guild.get_member(user)
                        if not user: user_data['friend_list'].remove(user.id)
                        else: await channel.set_permissions(user, view_channel=True, reason=f"Custom channel perk for {interaction.user}")
                    await self.bot.perk.update(perk.value, user_data)
                    await interaction.response.send_message(embed=discord.Embed(description="Your friend list has been fixed.", color=0x2b2d31))
    
    @app_commands.command(name="delete", description="delete your custom channel or role")
    @app_commands.describe(perk="the perk you want to delete")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Channel", value="channel"), app_commands.Choice(name="Custom Role", value="role")])
    async def _delete(self, interaction: Interaction, perk: app_commands.Choice[str]):
        user_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom channel or role. perk.", ephemeral=True)

        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description=f"Are you sure you want to delete your custom {perk.name.lower()}?", color=0x2b2d31), view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            match perk.value:
                case "channel":
                    channel = interaction.guild.get_channel(user_data['channel_id'])
                    if not channel: return await interaction.response.send_message("Your custom channel has been deleted/missing.", ephemeral=True)

                    total_seconds = (datetime.datetime.utcnow() - datetime.datetime(channel.created_at.year, channel.created_at.month, channel.created_at.day, channel.created_at.hour, channel.created_at.minute, channel.created_at.second)).total_seconds()
                    await channel.delete(reason=f"Custom channel perk for {interaction.user}")
                    user_data['channel_id'] = None
                    if user_data['duration'] != 'permanent': user_data['duration'] = round(user_data['duration'] - total_seconds)
                    await self.bot.perk.update(perk.value, user_data)
                    await view.interaction.response.edit_message(embed=discord.Embed(description="Your custom channel has been deleted.", color=0x2b2d31), view=None)

                case "role":
                    role = interaction.guild.get_role(user_data['role_id'])
                    if not role: return await view.interaction.response.send_message("Your custom role has been deleted/missing.", ephemeral=True)
                    total_seconds = (datetime.datetime.utcnow() - datetime.datetime(role.created_at.year, role.created_at.month, role.created_at.day, role.created_at.hour, role.created_at.minute, role.created_at.second)).total_seconds()
                    await role.delete(reason=f"Custom role perk for {interaction.user}")
                    user_data['role_id'] = None
                    if user_data['duration'] != 'permanent': user_data['duration'] = round(user_data['duration'] - total_seconds)
                    await self.bot.perk.update(perk.valueuser_data)
                    await view.interaction.response.edit_message(embed=discord.Embed(description="Your custom role has been deleted.", color=0x2b2d31), view=None)

    @app_commands.command(name="edit", description="edit your custom channel or role")
    @app_commands.describe(perk="the perk you want to edit", name="the name of your custom channel or role", color="the color of your custom role", icon="the icon of your custom role")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Channel", value="channels"), app_commands.Choice(name="Custom Role", value="roles")])
    async def edit(self, interaction: Interaction, perk: app_commands.Choice[str], name: str=None, color:str=None, icon: discord.Attachment=None):
        perk_data = await self.bot.perk.get_data(perk.value, interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message(f"You don't have any {perk.name.lower()} perks yet.", ephemeral=True)
        perk_config = await self.bot.perk.get("config", interaction.guild.id)

        match perk.value:
            case "channels":
                channel = interaction.guild.get_channel(perk_data['channel_id'])
                if not channel: return await interaction.response.send_message("Your channel perk is invalid/missing.", ephemeral=True)
                await interaction.response.send_message(embed=discord.Embed(description="Please wait while we edit your channel perk", color=0x2b2d31))
                if not name: await interaction.send_message(embed=discord.Embed(description="Please provide a name for your channel.", color=0x2b2d31))
                await channel.edit(name=name, reason=f"Custom channel perk for {interaction.user}")
                await interaction.response.send_message(embed=discord.Embed(description="Your channel has been edited.", color=0x2b2d31))
            case "roles":
                role = interaction.guild.get_role(perk_data['role_id'])
                if not role: return await interaction.response.send_message("Your role perk is invalid/missing.", ephemeral=True)
                await interaction.response.send_message(embed=discord.Embed(description="Please wait while we edit your role perk", color=0x2b2d31))
                if icon: 
                    if not icon.filename.url.endswith(('png', 'jpg')): return await interaction.send_message(embed=discord.Embed(description="Please provide a valid image for your role icon.", color=0x2b2d31))
                    async with self.bot.session.get(icon.filename.url) as resp:
                        if resp.status != 200: return await interaction.send_message(embed=discord.Embed(description="Please provide a valid image for your role icon.", color=0x2b2d31))
                        icon = await resp.read()
                color = color.replace("#", "") if color else None
                await role.edit(name=name, color=discord.Color(int(color, 16)) if color else role.color, reason=f"Custom role perk for {interaction.user}", display_icon=icon)
                await interaction.edit_original_response(embed=discord.Embed(description="Your role has been edited.", color=0x2b2d31))
    
    @app_commands.command(name="react", description="edit your react perk")
    @app_commands.describe(emoji="the emoji you want to react with")
    async def edit_react(self, interaction: Interaction, emoji: str):
        perk_data = await self.bot.perk.get_data('react', interaction.guild.id, interaction.user.id)
        if not perk_data: return await interaction.response.send_message("You don't have any react perks yet.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we check your emoji", color=0x2b2d31))
        message = await interaction.original_response()
        try:
            await message.add_reaction(emoji)
            await message.remove_reaction(emoji, self.bot.user)
        except:
            return await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji.", color=0x2b2d31))
        perk_data['emoji'] = emoji
        await self.bot.perk.update('react', perk_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Your Custom React as been set to {emoji}", color=0x2b2d31))
        await self.bot.perk.update_cache('react', interaction.user.id, interaction.guild.id, perk_data)

    @highlight.command(name="trigger", description="manage your highlight triggers")
    @app_commands.describe(trigger="The trigger for the highlight")
    @app_commands.choices(option=[app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove"), app_commands.Choice(name="List", value="list")])
    async def highlight_trigger(self, interaction: Interaction, option: app_commands.Choice[str], trigger: str):
        user_data = await self.bot.perk.get_data('highlight', interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any highlight perks yet.", ephemeral=True)
        if option.value == "add":
            if trigger in user_data['triggers']: return await interaction.response.send_message("This trigger already exists.", ephemeral=True)
            user_data['triggers'].append(trigger)
            await self.bot.perk.update('highlight', user_data)
            await interaction.response.send_message(embed=discord.Embed(description=f"`{trigger}` has been added to your highlight triggers.", color=0x2b2d31))
        elif option.value == "remove":
            if trigger not in user_data['triggers']: return await interaction.response.send_message("This trigger doesn't exist.", ephemeral=True)
            user_data['triggers'].remove(trigger)
            await self.bot.perk.update('highlight', user_data)
            await interaction.response.send_message(embed=discord.Embed(description=f"`{trigger}` has been removed from your highlight triggers.", color=0x2b2d31))
        elif option.value == "list":
            if not user_data['triggers']: return await interaction.response.send_message("You don't have any highlight triggers yet.", ephemeral=True)
            await interaction.response.send_message(embed=discord.Embed(description=f"Your highlight triggers are: `{', '.join(user_data['triggers'])}`", color=0x2b2d31))
        
        await self.bot.perk.update_cache('highlight', interaction.user.id, interaction.guild.id, user_data)
    
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
        self.update_cheche = self.update_perk_cache_task.start()
        self.role_task_in_progress = False
        self.channel_task_in_progress = False
    
    def cog_unload(self):
        self.role_perk_task_role.cancel()
        self.react_perk_channel.cancel()
        self.update_cheche.cancel()
    
    async def autoreact(self, message):
        if message.author.bot: return
        if message.guild is None: return
        if message.guild.id not in self.bot.perk.cach['react'].keys(): return

        for mention in message.mentions:
            if mention.id not in self.bot.perk.cach['react'][message.guild.id].keys(): continue
            user_data = self.bot.perk.cach['react'][message.guild.id][mention.id]
            if user_data['last_react'] is None:
                try:
                    await message.add_reaction(user_data['emoji'])
                except:
                    return
                user_data['last_react'] = datetime.datetime.utcnow()
                await self.bot.perk.update_cache('react', mention.id, message.guild.id, user_data)
                await self.bot.perk.update('react', user_data)
            elif (datetime.datetime.utcnow() - user_data['last_react']).total_seconds() > 30:
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

    @tasks.loop(minutes=60)
    async def update_perk_cache_task(self):
        await self.bot.perk.create_cach()
    
    @tasks.loop(seconds=10)
    async def check_perk_expire_role(self):
        if self.role_task_in_progress: return
        self.role_task_in_progress = True
        data = await self.bot.perk.roles.get_all()
        now = datetime.datetime.utcnow()
        for perks in data:
            guild = self.bot.get_guild(perks['guild_id'])
            if guild is None: continue
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
            if guild is None: continue
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
    
    @update_perk_cache_task.before_loop
    async def before_update_perk_cache(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_highlight(self, message: discord.Message, user_id: int,user_data: dict):
        messages = []
        async for msg in message.channel.history(limit=20, before=message):
            if msg.author.id == user_id:
                if not (datetime.datetime.utcnow() - datetime.datetime(msg.created_at.year, msg.created_at.month, msg.created_at.day, msg.created_at.hour, msg.created_at.minute, msg.created_at.second)).total_seconds() > 300:
                    return
            messages.append(msg)

        embed = discord.Embed(description="", color=0x2b2d31)
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
            pass
        user_data['last_trigger'] = datetime.datetime.utcnow()
        await self.bot.perk.update_cache('highlight', user_id, message.guild.id, user_data)
        await self.bot.perk.update('highlight', user_data)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.guild is None: return
        if len(message.mentions) > 0: await self.autoreact(message)
        await self.highlight(message)

class Perk_Config(commands.GroupCog, name="perk"):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="manage", description="Manage perks for your server members")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(option=[app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove"), app_commands.Choice(name="List", value="list")],perk=[app_commands.Choice(name="Custom Channel", value="channel"), app_commands.Choice(name="Custom Role", value="roles"), app_commands.Choice(name="Custom React", value="react"), app_commands.Choice(name="Highlight", value="highlight")])
    async def perk(self, interaction: Interaction, option: app_commands.Choice[str], perk: app_commands.Choice[str], member: discord.Member, duration: app_commands.Transform[int, TimeConverter]="permanent", friend_limit: app_commands.Range[int, 1, 10]=5):
        match option.value:
            case "add":
                perk_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
                if perk_data: return await interaction.response.send_message(embed=discord.Embed(description=f"{member.mention} already has this perk.", color=interaction.client.default_color))
                perk_data = await self.bot.perk.create(perk.value, member.id, interaction.guild.id, duration, friend_limit)
                await interaction.response.send_message(embed=discord.Embed(description=f"Successfully added {perk.name} to {member.mention}", color=interaction.client.default_color))
            case "remove":
                
                view = Confirm(interaction.user, 30)
                await interaction.response.send_message(embed=discord.Embed(description="Are you sure you want to remove this perk?", color=interaction.client.default_color), view=view)
                view.message = await interaction.original_response()
                await view.wait()
                if view.value:
                    match perk.value:
                        case "roles":
                            user_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
                            if not user_data: return await view.interaction.response.edit_message(embed=discord.Embed(description=f"{member.mention} does not have this perk.", color=interaction.client.default_color), view=None)
                            role = interaction.guild.get_role(user_data['role_id'])
                            if role is not None: await role.delete(reason=f"Perk Removed by {interaction.user}")
                            await self.bot.perk.delete(user_data)
                        case "channel":
                            user_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
                            if not user_data: return await view.interaction.response.edit_message(embed=discord.Embed(description=f"{member.mention} does not have this perk.", color=interaction.client.default_color), view=None)
                            channel = interaction.guild.get_channel(user_data['channel_id'])
                            if channel is not None: await channel.delete(reason=f"Perk Removed by {interaction.user}")
                            await self.bot.perk.delete(user_data)
                        case "react":
                            user_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
                            if not user_data: return await view.interaction.response.edit_message(embed=discord.Embed(description=f"{member.mention} does not have this perk.", color=interaction.client.default_color), view=None)
                            await self.bot.perk.delete(user_data)
                        case "highlight":
                            user_data = await self.bot.perk.get_data(perk.value, member.id, interaction.guild.id)
                            if not user_data: return await view.interaction.response.edit_message(embed=discord.Embed(description=f"{member.mention} does not have this perk.", color=interaction.client.default_color), view=None)
                            await self.bot.perk.delete(user_data)
                    await view.interaction.response.edit_message(embed=discord.Embed(description=f"Successfully removed {perk.value} from {member.mention}", color=interaction.client.default_color), view=None)
            case "list":
                        user_data = await self.bot.perk.get_data('all', interaction.guild.id, member.id)
                        if not user_data: return await interaction.response.send_message("You don't have any perks.", ephemeral=True)
                        pages = []
                        for perk, data in user_data.items():
                            embed = discord.Embed(title=f"{perk.capitalize()} perks", color=0x2b2d31, description="")
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

async def setup(bot):
    await bot.add_cog(Perks(bot))
    await bot.add_cog(Perk_Config(bot))
    await bot.add_cog(Perk_BackEND(bot))

