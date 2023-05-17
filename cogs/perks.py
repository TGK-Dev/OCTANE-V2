import enum
import discord
import datetime
import humanfriendly
import aiohttp
import re
from discord import Interaction, app_commands
from discord.app_commands import Group
from discord.ext import commands, tasks
from utils.db import Document
from typing import List, Literal, Union
from utils.transformer import MutipleChannel, TimeConverter
from utils.paginator import Paginator
from utils.views.buttons import Link_view, Confirm
from utils.views.perks_system import friends_manage
from colour import Color
class Perk_Type(enum.Enum):
    roles = "roles"
    channels = "channels"
    reacts = "reacts"
    highlights = "highlights"
    config = "config"


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
    
    async def get_data(self, type: Perk_Type | str, guild_id: int, user_id: int):
        match type:
            case Perk_Type.roles | "roles":
                return await self.roles.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.channels | "channels":
                return await self.channel.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.reacts | "reacts":
                return await self.react.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.highlights | "highlights":
                return await self.highlight.find({'guild_id': guild_id, 'user_id': user_id})
            case Perk_Type.config | "config":
                return await self.config.find({'_id': guild_id})
            case _:
                raise Exception("Invalid perk type")
    
    async def update(self, type: Perk_Type | str , data: dict):
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.update(data['_id'], data)

            case Perk_Type.channels | "channels":
                await self.channel.update(data['_id'], data)

            case Perk_Type.reacts | "reacts":
                await self.react.update(data['_id'], data)

            case Perk_Type.highlights | "highlights":
                await self.highlight.update(data['_id'], data)

            case Perk_Type.config | "config":
                await self.config.update(data['_id'], data)

            case _:
                raise Exception("Invalid perk type")

    async def delete(self, type: Perk_Type | str, data: dict):
        match type:
            case Perk_Type.roles | "roles":
                await self.roles.delete(data['_id'])

            case Perk_Type.channels | "channels":
                await self.channel.delete(data['_id'])

            case Perk_Type.reacts | "reacts":
                await self.react.delete(data['_id'])

            case Perk_Type.highlights | "highlights":
                await self.highlight.delete(data['_id'])

            case _:
                raise Exception("Invalid perk type")

    async def create(self, type: Perk_Type | str, user_id: int, guild_id: int, duration: Union[int, str], friend_limit: int=None):
        match type:
            case Perk_Type.roles | "roles":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'role_id': None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': []}
                await self.roles.insert(perk_data)
                return perk_data
            
            case Perk_Type.channels | "channels":
                perk_data = {'user_id': user_id,'guild_id': guild_id,'channel_id':None,'duration': duration,'created_at': None,'friend_limit': friend_limit,'friend_list': []}
                await self.channel.insert(perk_data)
                return perk_data
            
            case Perk_Type.reacts | "reacts":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'emoji': None, 'last_react': None}
                await self.react.insert(perk_data)
                return perk_data

            case Perk_Type.highlights | "highlights":
                perk_data = {'guild_id': guild_id, 'user_id': user_id, 'triggers': [], 'ignore_channel':[], 'ignore_users': [], 'last_trigger': None}
                await self.highlight.insert(perk_data)
                return perk_data
            
            case Perk_Type.config | "config":
                perk_config = {'_id': guild_id,'custom_category': None,'base_role_position': 0, 'admin_roles': []}
                await self.config.insert(perk_config)
                return perk_config
            
            case _:
                raise Exception("Invalid perk type")
    
    async def create_cach(self):
        configs = await self.config.get_all()
        await self.setup_reacts(configs)
        await self.setup_highlights(configs)
        return True
    
    async def setup_reacts(self, configs: list[dict]):
        reacts = await self.react.get_all()
        self.cach['react'] = {}
        for data in configs:
            if data['_id'] not in self.cach['react'].keys():
                self.cach['react'][data['_id']] = {}
        
        for react in reacts:
            if react['emoji'] != None:
                self.cach['react'][react['guild_id']][react['user_id']] = react
    
    async def setup_highlights(self, configs: list[dict]):
        highlights = await self.highlight.get_all()
        self.cach['highlight'] = {}
        for data in configs:
            if data['_id'] not in self.cach['highlight'].keys():
                self.cach['highlight'][data['_id']] = {}
        
        for highlight in highlights:
            self.cach['highlight'][highlight['guild_id']][highlight['user_id']] = highlight

    async def update_cache(self, perk: Perk_Type, guild: discord.Guild, data: dict):
        match perk:
            case Perk_Type.reacts:
                self.cach['react'][guild.id][data['user_id']] = data
            case Perk_Type.highlights:
                self.cach['highlight'][guild.id][data['user_id']] = data
            case _:
                raise Exception("Invalid perk type")

@app_commands.guild_only()
class Perks(commands.GroupCog, name="perks", description="manage your custom perks"):
    def __init__(self, bot):
        self.bot = bot
        self.role_perk_task = self.check_perk_expire_role.start()
        self.channel_perk_task = self.check_perk_expire_channel.start()
        self.refresh_cache_task = self.refresh_cache.start()
        self.role_task_in_progress = False
        self.channel_task_in_progress = False
        self.Perk: Perks_DB = Perks_DB(bot, Document)
        self.bot.Perk = self.Perk

    def cog_unload(self):
        self.role_perk_task.cancel()
        self.channel_perk_task.cancel()
        self.refresh_cache_task.cancel()
    
    async def highlight_remove_auto(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        user_data = await self.Perk.get_data(Perk_Type.highlights, interaction.guild.id, interaction.user.id)
        if user_data == None:
            return [
                app_commands.Choice(value="none", name="none")
            ]
        else:
            triggers_list = [
                app_commands.Choice(value=trigger, name=trigger)
                for trigger in user_data['triggers'] if current.lower() in trigger.lower()
            ]
            if len(triggers_list) == 0:
                triggers_list = [
                    app_commands.Choice(value=trigger, name=trigger)
                    for trigger in user_data['triggers']
                ]
            if len(user_data['triggers']) == 0:
                triggers_list = [
                    app_commands.Choice(value="none", name="none")
                ]
            return triggers_list[:24]

    admin = Group(name="admin", description="manage your custom perks")
    claim = Group(name="claim", description="claim your perks")
    react = Group(name="react", description="manage your react perks")
    edit = Group(name="edit", description="edit your perks")
    highlight = Group(name="highlight", description="manage your highlight perks")
    friend = Group(name="friend", description="give/revoke your custom role/channel access from your friends")
    delete = Group(name="delete", description="delete your perks temporarily")

    
    @admin.command(name="padd", description="add a custom perk to a user")
    @app_commands.describe(member="The member you want to manage", perk="The perk you want to manage", booster="Whether the perk is a booster or not", duration="The duration of the perk", friend_limit="The number of friends the user can give the perk to")
    async def _padd(self, interaction: Interaction, member: discord.Member, perk: Perk_Type, booster: bool,duration: app_commands.Transform[int, TimeConverter]="permanent", friend_limit: app_commands.Range[int, 1, 10]=3):
        config = await self.Perk.get_data(Perk_Type.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        if len(config['admin_roles']) == 0:
            await interaction.response.send_message("You need to setup admin roles first", ephemeral=True)
            return
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return

        if perk == Perk_Type.config:
            await interaction.response.send_message("You can't add config", ephemeral=True)
            return

        perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
        if perk_data:
            await interaction.response.send_message("This user already has this perk", ephemeral=True)
            return
        perk_data = await self.Perk.create(perk, member.id, interaction.guild.id, duration, friend_limit)
        await interaction.response.send_message(f"Successfully added {perk.name} to {member.mention}", ephemeral=True)
        if perk == Perk_Type.highlights:
            await interaction.channel.send(f"{member.mention} Now you can use </perks highlight tadd:1107680822301032469>")
        if perk == Perk_Type.reacts:
            await interaction.channel.send(f"{member.mention} Now you can use </perks react set:1107680822301032469>")
        if perk == Perk_Type.roles:
            await interaction.channel.send(f"{member.mention} Now you can use </perks claim role:1107680822301032469>")
        if perk == Perk_Type.channels:
            await interaction.channel.send(f"{member.mention} Now you can use </perks claim channel:1107680822301032469>")
    
    @admin.command(name="premove", description="remove a custom perk from a user")
    @app_commands.describe(member="The member you want to manage", perk="The perk you want to manage")
    @app_commands.checks.has_permissions(administrator=True)
    async def _premove(self, interaction: Interaction, member: discord.Member, perk: Perk_Type):

        config = await self.Perk.get_data(Perk_Type.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        if len(config['admin_roles']) == 0:
            await interaction.response.send_message("You need to setup admin roles first", ephemeral=True)
            return
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return
        
        if perk == Perk_Type.config:
            await interaction.response.send_message("You can't remove config", ephemeral=True)
            return
        perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
        if not perk_data:
            await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
            return
        await self.Perk.delete(perk, perk_data)
        await interaction.response.send_message(f"Successfully removed {perk.name} from {member.mention}", ephemeral=False)

        if perk == Perk_Type.channels:
            channel = interaction.guild.get_channel(perk_data['channel_id'])
            if channel: await channel.delete(reason=f"Perk Removed By {interaction.user.name}")
        
        if perk == Perk_Type.roles:
            role = interaction.guild.get_role(perk_data['role_id'])
            if role: await role.delete(reason=f"Perk Removed By {interaction.user.name}")

    # @admin.command(name="pinfo", description="get info about a user's custom perk")
    # @app_commands.describe(member="The member you want to manage", perk="The perk you want to get info about")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def _pinfo(self, interaction: Interaction, member: discord.Member, perk: Perk_Type):

    #     config = await self.Perk.get_data(Perk_Type.config, interaction.guild.id, interaction.user.id)
    #     if config == None:
    #         await interaction.response.send_message("You need to setup config first", ephemeral=True)
    #         return
    #     if len(config['admin_roles']) == 0:
    #         await interaction.response.send_message("You need to setup admin roles first", ephemeral=True)
    #         return
        
    #     user_roles = [role.id for role in interaction.user.roles]
    #     if (set(user_roles) & set(config['admin_roles'])) == set():
    #         await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
    #         return

    #     match perk:
    #         case Perk_Type.reacts:
    #             perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
    #             if not perk_data:
    #                 await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
    #                 return
    #             else:
    #                 embed = discord.Embed(description=f"**Emoji:** {perk_data['emoji']}", color=interaction.client.default_color)
    #                 await interaction.response.send_message(embed=embed, ephemeral=False)
    #                 return
    #         case Perk_Type.highlights:
    #             perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
    #             if not perk_data:
    #                 embed = discord.Embed(description=f"This user doesn't have this perk", color=interaction.client.default_color)
    #                 await interaction.response.send_message(embed=embed, ephemeral=True)
    #                 return
    #             else:
    #                 embed = discord.Embed(title="Highlights Perk", description="")
    #                 embed.description += f"Trigger: {','.join(perk_data['trigger']) if perk_data['trigger'] else 'None'}\n"
    #                 embed.description += f"Ignore Channels: {','.join([f'<#{channel}>' for channel in perk_data['ignore_channels']]) if perk_data['ignore_channels'] else 'None'}\n"
    #                 embed.description += f"Ignore Users: {','.join([f'<@{user}>' for user in perk_data['ignore_users']]) if perk_data['ignore_users'] else 'None'}\n"
    #                 await interaction.response.send_message(embed=embed, ephemeral=False)
    #                 return
    #         case Perk_Type.roles:
    #             perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
    #             if not perk_data:
    #                 await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
    #                 return
    #             if not perk_data['role_id']:
    #                 await interaction.response.send_message("This user doesn't yet have to claim their role", ephemeral=True)
    #                 return
    #             else:
    #                 role = interaction.guild.get_role(perk_data['role_id'])
    #                 embed = discord.Embed(title="Custom Role Perk")
    #                 if role.display_icon: embed.set_thumbnail(url=role.display_icon.url)
    #                 embed.add_field(name="Owner", value=member.mention, inline=True)
    #                 embed.add_field(name="Role", value=role.mention, inline=True)
    #                 embed.add_field(name="Created", value=f"<t:{round(role.created_at.timestamp)}>", inline=True)
    #                 embed.add_field(name="Duration", value="Permanent" if perk_data['duration'] == 'permanent' else f"<t:{round(discord.utils.utcnow() + datetime.timedelta(seconds=perk_data['duration']))}:R>", inline=True)
    #                 embed.add_field(name="Friend Limit", value=perk_data['friend_limit'], inline=True)
    #                 embed.add_field(name="Friends", value=f"{','.join([f'<@{friend}>' for friend in perk_data['friends']]) if perk_data['friends'] else 'None'}", inline=True)
    #                 await interaction.response.send_message(embed=embed, ephemeral=False)
    #                 return
    #         case Perk_Type.channels:
    #             perk_data = await self.Perk.get_data(perk, interaction.guild.id, member.id)
    #             if not perk_data:
    #                 await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
    #                 return
    #             if not perk_data['channel_id']:
    #                 await interaction.response.send_message("This user doesn't yet have to claim their channel", ephemeral=True)
    #                 return
    #             else:
    #                 channel = interaction.guild.get_channel(perk_data['channel_id'])
    #                 embed = discord.Embed(title="Custom Channel Perk")
    #                 embed.add_field(name="Owner", value=member.mention, inline=True)
    #                 embed.add_field(name="Channel", value=channel.mention, inline=True)
    #                 embed.add_field(name="Created", value=f"<t:{round(channel.created_at.timestamp)}>", inline=True)
    #                 embed.add_field(name="Duration", value="Permanent" if perk_data['duration'] == 'permanent' else f"<t:{round(discord.utils.utcnow() + datetime.timedelta(seconds=perk_data['duration']))}:R>", inline=True)
    #                 embed.add_field(name="Friend Limit", value=perk_data['friend_limit'], inline=True)
    #                 embed.add_field(name="Friends", value=f"{','.join([f'<@{friend}>' for friend in perk_data['friends']]) if perk_data['friends'] else 'None'}", inline=True)
    #                 await interaction.response.send_message(embed=embed, ephemeral=False)
    #                 return
    #         case _:
    #             await interaction.response.send_message("This Perk is not Viewable", ephemeral=True)

    @claim.command(name="role", description="claim your custom role")
    @app_commands.describe(name="The name of the role you want to claim", color="The color of the role you want to claim", icon="The icon of the role you want to claim")
    async def claim_role(self, interaction: Interaction, name: str, color: str, icon: discord.Attachment=None):
        user_data = await self.Perk.get_data(Perk_Type.roles, interaction.guild.id, interaction.user.id)
        if not user_data:
            await interaction.response.send_message("You don't have any custom role perks", ephemeral=True)
            return

        if user_data['role_id']:
            await interaction.response.send_message("You already have a custom role", ephemeral=True)
            return
        
        await interaction.response.send_message(embed=discord.Embed(description="Processing your request", color=interaction.client.default_color))

        if icon:
            if not icon.filename.endswith(("png", "jpg")):
                await interaction.edit_original_response(embed=discord.Embed(description="Invalid file type", color=interaction.client.default_color))
                return
            
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status != 200:
                        await interaction.edit_original_response(embed=discord.Embed(description="Failed to download the icon", color=interaction.client.default_color))
                        return

                    icon = await resp.read()
        
        if "#" not in color:
            await interaction.edit_original_response(embed=discord.Embed(description="Invalid color make sure to add `#` before the hex code", color=interaction.client.default_color))
        color = tuple(round(c*255) for c in Color(color).rgb)
        color = discord.Color.from_rgb(*color)

        config = await self.Perk.get_data(Perk_Type.config, interaction.guild.id, interaction.user.id)
        position_role = interaction.guild.get_role(config['base_role_position'])
        position = position_role.position + 1
        role = await interaction.guild.create_role(name=name, color=color, display_icon=icon)
        await role.edit(position=position)
        user_data['role_id'] = role.id
        await self.Perk.update(Perk_Type.roles, user_data)

        await interaction.user.add_roles(role)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Your role {role.mention} has been created", color=interaction.client.default_color))
    
    @claim.command(name="channel", description="claim your custom channel")
    @app_commands.describe(name="The name of the channel you want to claim", topic="The topic of the channel you want to claim")
    async def claim_channel(self, interaction: Interaction, name: str, topic: str):
        user_data = await self.Perk.get_data(Perk_Type.channels, interaction.guild.id, interaction.user.id)
        if not user_data:
            await interaction.response.send_message("You don't have any custom channel perks", ephemeral=True)
            return
        
        if user_data['channel_id']:
            await interaction.response.send_message("You already have a custom channel", ephemeral=True)
            return
        
        await interaction.response.send_message(embed=discord.Embed(description="Processing your request", color=interaction.client.default_color))

        config = await self.Perk.get_data(Perk_Type.config, interaction.guild.id, interaction.user.id)
        position_channel = interaction.guild.get_channel(config['custom_category'])
        robot_role = interaction.guild.get_role(810153515610537994)
        overwrite = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
        }
        if robot_role:
            overwrite[robot_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

        channel = await interaction.guild.create_text_channel(name=name, topic=topic, overwrites=overwrite, category=position_channel)
        user_data['channel_id'] = channel.id
        await self.Perk.update(Perk_Type.channels, user_data)

        msg = await channel.send(f"Welcome to your custom channel {interaction.user.mention}")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Your Channel", style=discord.ButtonStyle.url, url=msg.jump_url))
        await interaction.edit_original_response(embed=discord.Embed(description=f"Your channel {channel.mention} has been created", color=interaction.client.default_color), view=view)

    @app_commands.command(name="friend", description="manage your friends list")
    @app_commands.describe(perk="The perk you want to manage")
    @app_commands.choices(perk=[app_commands.Choice(name=Perk_Type.roles.value, value=Perk_Type.roles.value), app_commands.Choice(name=Perk_Type.channels.value, value=Perk_Type.channels.value)])
    async def _friend(self, interaction: Interaction, perk: app_commands.Choice[str]):
        match perk.value:
            case Perk_Type.roles | "roles":
                user_data = await self.Perk.get_data(Perk_Type.roles, interaction.guild.id, interaction.user.id)
                if not user_data:
                    await interaction.response.send_message("You don't have any custom role perks", ephemeral=True)
                    return
                if not user_data['role_id']:
                    await interaction.response.send_message("You don't yet have to claim your custom role", ephemeral=True)
                    return
                role = interaction.guild.get_role(user_data['role_id'])
                if not role:
                    await interaction.response.send_message("Your custom role has been deleted or you have not claimed it yet", ephemeral=True)
                    user_data['role_id'] = None
                    await self.Perk.update(Perk_Type.roles, user_data)
                    return
                embed = discord.Embed(title=f"{interaction.user}'s Custom Role Friends", color=interaction.client.default_color if not role.color else role.color, description="")
                embed.description += f"**Friends Limit:** {user_data['friend_limit']}\n"
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in user_data['friend_list']])
                embed.add_field(name="Friends", value=friends if friends else "`No Friends ;(`")
                view = friends_manage(interaction.user, user_data, "roles")
                await interaction.response.send_message(embed=embed, view=view)
                view.message = await interaction.original_response()
                return
    
            case Perk_Type.roles | "channels":
                user_data = await self.Perk.get_data(Perk_Type.channels, interaction.guild.id, interaction.user.id)
                if not user_data:
                    await interaction.response.send_message("You don't have any custom channel perks", ephemeral=True)
                    return
                if not user_data['channel_id']:
                    await interaction.response.send_message("You don't yet have to claim your custom channel", ephemeral=True)
                    return
                
                channel = interaction.guild.get_channel(user_data['channel_id'])
                if not channel:
                    await interaction.response.send_message("Your custom channel has been deleted or you have not claimed it yet", ephemeral=True)
                    user_data['channel_id'] = None
                    await self.Perk.update(Perk_Type.channels, user_data)
                    return
                
                embed = discord.Embed(title=f"{interaction.user}'s Custom Channel Friends", color=interaction.client.default_color, description="")
                embed.description += f"**Friends Limit:** {user_data['friend_limit']}\n"
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in user_data['friend_list']])
                embed.add_field(name="Friends", value=friends if friends else "`No Friends ;(`")
                view = friends_manage(interaction.user, user_data, "channels")
                await interaction.response.send_message(embed=embed, view=view)
                view.message = await interaction.original_response()
                return
    

    @edit.command(name="role", description="edit your custom role")
    @app_commands.describe(name="The new name of your custom role", color="The new color of your custom role", icon="The new icon of your custom role")
    @app_commands.checks.cooldown(1, 120, key= lambda i: (i.guild.id, i.user.id))
    async def _edit_role(self, interaction: discord.Interaction, name: str=None, color:str=None, icon: discord.Attachment=None):    

        if not name and not color and not icon:
            return await interaction.response.send_message("You must provide a name or color to edit your custom role", ephemeral=True)
        user_data = await self.Perk.get_data(Perk_Type.roles, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You don't have any custom role perks", ephemeral=True)
        if not user_data['role_id']:
            return await interaction.response.send_message("You don't yet have to claim your custom role", ephemeral=True)
        

        role = interaction.guild.get_role(user_data['role_id'])
        if not role:
            await interaction.response.send_message("Your custom role has been deleted or you have not claimed it yet", ephemeral=True)
            user_data['role_id'] = None
            await self.Perk.update(Perk_Type.roles, user_data)
            return
        
        await interaction.response.send_message(embed=discord.Embed(description="Editing your custom role...", color=interaction.client.default_color))

        if name:
            await role.edit(name=name)
        if color:
            if "#" not in color:
                await interaction.edit_original_response(embed=discord.Embed(description="Invalid color make sure to add `#` before the hex code", color=interaction.client.default_color))
            color = tuple(round(c*255) for c in Color(color).rgb)
            color = discord.Color.from_rgb(*color)
            await role.edit(color=color)

        if icon:
            if not icon.filename.endswith(("png", "jpg")):
                await interaction.edit_original_response(embed=discord.Embed(description="Invalid file type", color=interaction.client.default_color))
                return
            
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status != 200:
                        await interaction.edit_original_response(embed=discord.Embed(description="Failed to download the icon", color=interaction.client.default_color))
                        return

                    icon = await resp.read()
            
            await role.edit(display_icon=icon)
        
        await interaction.edit_original_response(embed=discord.Embed(description="Your custom role has been edited", color=interaction.client.default_color))
    
    @edit.command(name="channel", description="edit your custom channel")
    @app_commands.describe(name="The new name of your custom channel", topic="The new topic of your custom channel")
    @app_commands.checks.cooldown(1, 120, key= lambda i: (i.guild.id, i.user.id))
    async def _edit_channel(self, interaction: discord.Interaction, name: str=None, topic: str=None):
        if not name and not topic:
            return await interaction.response.send_message("You must provide a name or topic to edit your custom channel", ephemeral=True)
        user_data = await self.Perk.get_data(Perk_Type.channels, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You don't have any custom channel perks", ephemeral=True)
        if not user_data['channel_id']:
            return await interaction.response.send_message("You don't yet have to claim your custom channel", ephemeral=True)
        
        channel = interaction.guild.get_channel(user_data['channel_id'])
        if not channel:
            await interaction.response.send_message("Your custom channel has been deleted or you have not claimed it yet", ephemeral=True)
            user_data['channel_id'] = None
            await self.Perk.update(Perk_Type.channels, user_data)
            return
        
        if name:
            await channel.edit(name=name)
        if topic:
            await channel.edit(topic=topic)

    @app_commands.command(name="delete", description="delete your custom channel or role")
    @app_commands.describe(perk="the perk you want to delete")
    @app_commands.choices(perk=[app_commands.Choice(name="Custom Channel", value="channel"), app_commands.Choice(name="Custom Role", value="role")])
    async def _delete(self, interaction: Interaction, perk: app_commands.Choice[str]):
        if perk == "channel":
            user_data = await self.Perk.get_data(Perk_Type.channels, interaction.guild.id, interaction.user.id)
            if not user_data: return await interaction.response.send_message("You don't have any custom channel perks", ephemeral=True)
        elif perk == "role":
            user_data = await self.Perk.get_data(Perk_Type.roles, interaction.guild.id, interaction.user.id)
            if not user_data: return await interaction.response.send_message("You don't have any custom role perks", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid perk", ephemeral=True)

        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description=f"Are you sure you want to delete your {perk.name}?", color=interaction.client.default_color), view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.value:
            if perk == "channel":
                channel = interaction.guild.get_channel(user_data['channel_id'])
                if channel:
                    total_time = (datetime.datetime.utcnow() - datetime.datetime(channel.created_at.year, channel.created_at.month, channel.created_at.day)).total_seconds()
                    duraction = user_data['duration'] - total_time
                    user_data['duration'] = duraction
                    await self.Perk.update(Perk_Type.channels, user_data)
                try:
                    await interaction.user.send("Your has been deleted successfully")
                except:
                    pass
                user_data['channel_id'] = None
                await self.Perk.update(Perk_Type.channels, user_data)
        
            elif perk == "role":
                role = interaction.guild.get_role(user_data['role_id'])
                if role:
                    total_time = (datetime.datetime.utcnow() - datetime.datetime(role.created_at.year, role.created_at.month, role.created_at.day)).total_seconds()
                    duraction = user_data['duration'] - total_time
                    user_data['duration'] = duraction
                    await self.Perk.update(Perk_Type.roles, user_data)
                    await role.delete()
                try:
                    await interaction.user.send("Your has been deleted successfully")
                except:
                    pass
                user_data['role_id'] = None
                await self.Perk.update(Perk_Type.roles, user_data)

            await view.interaction.response.edit_message(embed=discord.Embed(description=f"Your {perk.name} has been deleted successfully", color=interaction.client.default_color), view=None)
        else:
            await view.interaction.response.edit_message(embed=discord.Embed(description=f"Timed out", color=interaction.client.default_color), view=None)

    @react.command(name="set", description="set your custom auto reaction perk")
    @app_commands.describe(emoji="the emoji you want to set")
    async def _set(self, interaction: Interaction, emoji: str):
        user_data = await self.Perk.get_data(Perk_Type.reacts, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any custom reaction perks", ephemeral=True)

        await interaction.response.send_message(embed=discord.Embed(description="Checking emoji...", color=interaction.client.default_color))
        msg = await interaction.original_response()
        try:
            await msg.add_reaction(emoji)
        except:
            await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji", color=interaction.client.default_color))
            return
        
        user_data['emoji'] = emoji
        await self.Perk.update(Perk_Type.reacts, user_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Your custom reaction has been set to {emoji}", color=interaction.client.default_color))
        await self.Perk.update_cache(Perk_Type.reacts, interaction.guild, user_data)


    @highlight.command(name="tadd", description="add a trigger to your highlight perk")
    @app_commands.describe(trigger="the trigger you want to add")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def highlight_trigger(self, interaction: Interaction, trigger: str):
        user_data = await self.Perk.get_data(Perk_Type.highlights, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any highlight perks", ephemeral=True)
        if len(user_data['triggers']) >= 10: return await interaction.response.send_message("You have reached the maximum amount of triggers", ephemeral=True)      
        if trigger.lower() in user_data['triggers']: return await interaction.response.send_message("You already have that trigger", ephemeral=True)

        user_data['triggers'].append(trigger.lower())
        await self.Perk.update(Perk_Type.highlights, user_data)
        await self.Perk.update_cache(Perk_Type.highlights, interaction.guild, user_data)

        await interaction.response.send_message(f"Your trigger `{trigger}` has been added", ephemeral=True)
    
    @highlight.command(name="tremove", description="remove a trigger from your highlight perk")
    @app_commands.describe(trigger="the trigger you want to remove")
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.autocomplete(trigger=highlight_remove_auto)
    async def highlight_trigger_remove(self, interaction: Interaction, trigger: str):
        user_data = await self.Perk.get_data(Perk_Type.highlights, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any highlight perks", ephemeral=True)
        if trigger.lower() not in user_data['triggers']: return await interaction.response.send_message("You don't have that trigger", ephemeral=True)

        user_data['triggers'].remove(trigger.lower())
        await self.Perk.update(Perk_Type.highlights, user_data)
        await self.Perk.update_cache(Perk_Type.highlights, interaction.guild, user_data)

        await interaction.response.send_message(f"Your trigger `{trigger}` has been removed", ephemeral=True)
    
    @tasks.loop(seconds=10)
    async def check_perk_expire_role(self):
        if self.role_task_in_progress: return
        self.role_task_in_progress = True
        data = await self.Perk.roles.get_all()
        now = datetime.datetime.utcnow()

        for perks in data:
            guild = self.bot.get_guild(perks['guild_id'])
            if guild is None: continue
            user = guild.get_member(perks['user_id'])
            if not user:
                role = guild.get_role(perks['role_id'])
                if role: await role.delete(reason="User left the server/not found")
                await self.Perk.delete(Perk_Type.roles, perks)
            if perks['duration'] == 'permanent': continue
            if perks['role_id'] is None: continue
            role = guild.get_role(perks['role_id'])
            if not role: continue
            role_created_at = datetime.datetime.utcfromtimestamp(role.created_at.timestamp())
            if now > role_created_at + datetime.timedelta(seconds=perks['duration']):
                await role.delete(reason="Custom role expired")
                await self.Perk.delete(Perk_Type.roles, perks)
                try:
                    embed = discord.Embed(title="Custom Role Expired", description=f"Your custom role `@{role.name}` in **{guild.name}** has expired and has been removed.", color=self.bot.default_color)
                    await user.send(embed=embed)
                except:
                    pass
        self.role_task_in_progress = False
    
    @tasks.loop(seconds=10)
    async def check_perk_expire_channel(self):
        if self.channel_task_in_progress: return
        self.channel_task_in_progress = True
        data = await self.Perk.channel.get_all()
        now = discord.utils.utcnow()
        for perks in data:
            guild = self.bot.get_guild(perks['guild_id'])
            if guild is None: continue
            user = guild.get_member(perks['user_id'])
            if not user:
                channel = guild.get_channel(perks['channel_id'])
                if channel: await channel.delete(reason="User left the server/not found")
                await self.Perk.delete(Perk_Type.channels, perks)
            if perks['duration'] == 'permanent': continue
            if perks['channel_id'] is None: continue
            channel = guild.get_channel(perks['channel_id'])
            if not channel: continue
            channel_created_at = channel.created_at
            if now > channel_created_at + datetime.timedelta(seconds=perks['duration']):
                await channel.delete(reason="Custom channel expired")
                await self.Perk.delete(Perk_Type.channels, perks)
                try:
                    embed = discord.Embed(title="Custom channel expired", description=f"Your custom channel `#{channel.name}` in **{guild.name}** has expired and has been removed.", color=self.bot.default_color)
                    await user.send(embed=embed)
                except:
                    pass
            else:
                pass
        self.channel_task_in_progress = False
    
    @tasks.loop(hours=3)
    async def refresh_cache(self):
        await self.Perk.create_cach()
    
    @check_perk_expire_channel.before_loop
    async def before_check_perk_expire_channel(self):
        await self.bot.wait_until_ready()
    
    @check_perk_expire_role.before_loop
    async def before_check_perk_expire_role(self):
        await self.bot.wait_until_ready()

    @refresh_cache.before_loop
    async def before_refresh_cache(self):
        await self.bot.wait_until_ready()
    

    @commands.Cog.listener()
    async def on_ready(self):
        await self.Perk.create_cach()


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if len(message.mentions) > 0:
            self.bot.dispatch('auto_react', message)
        if message.content is not None or message.content != "":
            self.bot.dispatch('auto_highlight', message)
    
    @commands.Cog.listener()
    async def on_auto_highlight(self, message: discord.Message):
        if message.guild.id not in self.Perk.cach['highlight'].keys(): return
        guild_data = self.Perk.cach['highlight'][message.guild.id]
        message_content = message.content.lower()
        message_content = message_content.split(" ")

        for word in message_content:
            for user_data in guild_data:
                word = str(word)
                user_data = guild_data[user_data]
                if word in user_data['triggers']:
                    user = message.guild.get_member(user_data['user_id'])
                    perm = message.channel.permissions_for(user)
                    if not perm.view_channel or perm.view_channel == False: continue
                    self.bot.dispatch('highlight_found', message, user_data)
                    continue
    
    @commands.Cog.listener()
    async def on_highlight_found(self, message: discord.Message, user_data: dict):
        now = datetime.datetime.utcnow()
        user = message.guild.get_member(user_data['user_id'])

        if user_data['last_trigger'] is not None:
            if not now > user_data['last_trigger'] + datetime.timedelta(minutes=15):
                return
        
        before_messages = [message async for message in message.channel.history(limit=10, before=message)]
        embed = discord.Embed(title=f"Hightlight found in {message.guild.name}", color=self.bot.default_color, description="")
        before_messages.reverse()
        for bmessage in before_messages:
            if bmessage.id == user_data['user_id']:
                if not now > message.created_at + datetime.timedelta(minutes=5): return
                pass
            embed.description += f"**[{bmessage.created_at.strftime('%H:%M:%S')}] {bmessage.author.display_name}:** {bmessage.content}\n"        
        embed.add_field(name="Trigger Message", value=f"[{message.created_at.strftime('%H:%M:%S')}] {message.author.display_name}: {message.content}", inline=False)
        embed.set_footer(text=f"Triggered by {user.display_name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else user.default_avatar)
        try:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", url=message.jump_url, style=discord.ButtonStyle.url, emoji="<:tgk_link:1105189183523401828>"))
            await user.send(embed=embed, view=view)
        except:
            pass
        user_data['last_trigger'] = now
        await self.Perk.update_cache(Perk_Type.highlights, message.guild, user_data)
        await self.Perk.update(Perk_Type.highlights, user_data)

    @commands.Cog.listener()
    async def on_auto_react(self, message: discord.Message):
        if len(message.mentions) == 0: return
        if message.guild.id not in self.Perk.cach['react'].keys(): return
        guild_data = self.Perk.cach['react'][message.guild.id]
        now = datetime.datetime.utcnow()
        for mention in message.mentions:
            if mention.id in guild_data.keys():
                user_data = guild_data[mention.id]
                if user_data['last_react'] is None:
                    try:
                        await message.add_reaction(user_data['emoji'])
                    except:
                        continue
                    user_data['last_react'] = datetime.datetime.utcnow()
                    await self.Perk.update_cache(Perk_Type.reacts, message.guild, user_data)
                else:
                    if now > user_data['last_react'] + datetime.timedelta(seconds=20):
                        try:
                            await message.add_reaction(user_data['emoji'])
                        except:
                            continue
                        user_data['last_react'] = datetime.datetime.utcnow()
                        await self.Perk.update_cache(Perk_Type.reacts, message.guild, user_data)

async def setup(bot):
    await bot.add_cog(Perks(bot))
    #await bot.add_cog(Perk_BackEND(bot))

