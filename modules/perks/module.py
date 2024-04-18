import io
import aiohttp
import random
import discord
import datetime
import humanfriendly
import aiohttp
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from utils.db import Document
from typing import List, Literal
from .views import Friends_manage, Perk_Ignore, Emoji_Request
from utils.embed import get_formated_embed, get_formated_field
from colour import Color
from utils.checks import Blocked
from .db import Perk_Type, Perks_DB, Custom_Channel, Profile, Config, Custom_Roles

time = datetime.time(hour=4, minute=30, tzinfo=datetime.timezone.utc)
class Perks(commands.Cog, name="perk", description="manage your custom perks"):
    def __init__(self, bot):
        self.bot = bot
        self.backend: Perks_DB = Perks_DB(bot, Document)
        self.refresh_cache.start()
        self.profile_roles.start()
        self.profile_reacts.start()
        self.profile_channels.start()
        self.bot.Perk = self.backend
    
    def cog_unload(self):
        self.profile_channels.cancel()
        self.refresh_cache.cancel()
        self.profile_roles.cancel()
    
    async def interaction_check(self, interaction: discord.Interaction):
        data = await self.backend.bans.find({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
        if data:
            raise Blocked(interaction)
        else:
            return True

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Emoji_Request())
        await self.backend.create_cach()

    @tasks.loop(hours=3)
    async def refresh_cache(self):
        await self.backend.create_cach()

    @refresh_cache.before_loop
    async def before_refresh_cache(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=time)
    async def profile_roles(self):
        role_data = await self.backend.roles.get_all()
        for data in role_data:
            self.bot.dispatch("check_profile_roles", data)
        
    @profile_roles.before_loop
    async def before_profile_roles(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_check_profile_roles(self, data: Custom_Roles):
        guild: discord.Guild = self.bot.get_guild(data['guild_id'])
        if not guild: return
        crole: discord.Role = guild.get_role(data['role_id'])
        if not crole: return
        config = await self.backend.get_data(self.backend.types.config, guild.id, self.bot.user.id)
        if not config: return

        user: discord.Member = guild.get_member(data['user_id'])
        if not isinstance(user, discord.Member):
            if crole:
                await crole.delete()
            log_channel = guild.get_channel(1186937287183958056)
            if log_channel:
                await log_channel.send(f"**User**: {data['user_id']} has left the server and his custom role `{crole.name}` will been deleted")
            await self.backend.delete(self.backend.types.roles, data)
            
            return    

        total_duraction = 0
        total_share_limit = 0

        for key, item in config['profiles']['roles'].items():
            role = guild.get_role(int(key))
            if not role: 
                del config['profiles']['roles'][key]
                await self.backend.update(self.backend.types.config, config)
                continue
            if role in user.roles:
                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']
                if total_share_limit < 30: total_share_limit += item['share_limit']
                elif total_share_limit >= 30: total_share_limit = 30

        if total_share_limit == 0:
            total_share_limit = 3

        if data['freeze']['share_limit'] is not True:
            data['share_limit'] = total_share_limit
            data['duration'] = total_duraction

        await self.backend.update(self.backend.types.roles, data)

        if total_duraction == 0 and data['freeze']["delete"] is not True:
            channel = guild.get_channel(1190668526361518120)
            if channel:
                await channel.send(f"**User**: {user.mention} is going to lose his custom role `{crole.name}`", allowed_mentions=discord.AllowedMentions.none())
            try:
                await user.send(embed=discord.Embed(description=f"Your custom role `{role.name}` has been deleted because you have no active custom roles", color=self.bot.default_color))
            except:
                pass
                
            role = guild.get_role(data['role_id'])
            if role: 
                await role.delete()
            await self.backend.delete(self.backend.types.roles, data)

            return
    

    @tasks.loop(time=time)
    async def profile_channels(self):
        channel_data = await self.backend.channel.get_all()
        for data in channel_data:
            self.bot.dispatch("check_profile_channels", data)
        
    @profile_channels.before_loop
    async def before_profile_channels(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_check_profile_channels(self, data: Custom_Channel):
        guild: discord.Guild = self.bot.get_guild(data['guild_id'])
        config = await self.backend.get_data(self.backend.types.config, guild.id, data['user_id'])
        if not guild: return

        user = guild.get_member(data['user_id'])
        channel = guild.get_channel(data['channel_id'])
        if not isinstance(user, discord.Member): 
            if channel:
                await channel.delete()
            log_channel = guild.get_channel(1190668526361518120)
            if log_channel:
                await log_channel.send(f"**User**: {data['user_id']} has left the server and his custom channel `{channel.name}` has been deleted")
            
            await self.backend.delete(self.backend.types.channels, data)            
            return
        
        total_duraction = 0
        total_share_limit = 0

        for key, item in config['profiles']['channels'].items():
            role = guild.get_role(int(key))
            item: Profile = item

            if not role: 
                del config['profiles']['channels'][key]
                await self.backend.update(self.backend.types.config, config)
                continue
            if role in user.roles:
                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']
                if total_share_limit < 30: total_share_limit += item['share_limit']
                elif total_share_limit >= 30: total_share_limit = 30

        if data['freeze']['share_limit'] is not True:
            data['share_limit'] = total_share_limit

        data['duration'] = total_duraction

        await self.backend.update(self.backend.types.channels, data)

        if total_duraction == 0 and data['freeze']["delete"] is not True:
            channel = guild.get_channel(1186937287183958056)
            if channel:
                await channel.send(f"**User**: {user.mention} is going to lose his custom channel `{channel.name}`")
            try:
                await user.send(embed=discord.Embed(description=f"Your custom channel `{channel.name}` has been deleted because you have no active custom channels", color=self.bot.default_color))
            except:
                pass

            await self.backend.delete(self.backend.types.channels, data)
            await channel.delete()
        return
    
    @tasks.loop(time=time)
    async def profile_reacts(self):
        react_data = await self.backend.react.get_all()
        for data in react_data:
            self.bot.dispatch("check_profile_reacts", data)
    
    @profile_reacts.before_loop
    async def before_profile_reacts(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=time)
    async def check_channel_activity(self):
        config = await self.backend.config.get_all()
        for data in config:
            guild: discord.Guild = self.bot.get_guild(data['guild_id'])
            channels: List[Custom_Channel] = await self.backend.channel.find_many_by_custom({'guild_id': data['guild_id']})
            for channel in channels:
                if (datetime.datetime.utcnow() - channel["activity"]['last_message']).days() >= 7:
                    channel_owner = guild.get_member(channel['user_id'])
                    chanel = guild.get_channel(channel['channel_id'])
                    try:
                        await channel_owner.send(embed=discord.Embed(description=f"Your custom channel {chanel.name} in {guild.name} has been deleted because it has been inactive for more than 7 days", color=self.bot.default_color))
                    except:
                        pass
                    await self.backend.delete(self.backend.types.channels, channel)
                    await chanel.delete()

    @check_channel_activity.before_loop
    async def before_check_channel_activity(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_check_profile_reacts(self, data: dict):
        guild: discord.Guild = self.bot.get_guild(data['guild_id'])
        if not guild: return
        config = await self.backend.get_data(self.backend.types.config, guild.id, data['user_id'])
        if not config: return

        user = guild.get_member(data['user_id'])

        if not isinstance(user, discord.Member): 
            await self.backend.delete(self.backend.types.reacts, data)
            del self.backend.cach['react'][data['guild_id']][data['user_id']]
            return
        
        total_duraction = 0
        total_reaction_limit = 0

        for key, item in config['profiles']['reacts'].items():
            role = guild.get_role(int(key))
            if not role: 
                del config['profiles']['reacts'][key]
                await self.backend.update(self.backend.types.config, config)
                continue
            if role in user.roles:
                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']
                if total_reaction_limit < 10: total_reaction_limit += item['share_limit']
                elif total_reaction_limit >= 10: total_reaction_limit = 10

        if total_duraction == 0:
            chal = self.bot.get_channel(1190668526361518120)
            await chal.send(f"**User**: {user.mention} is going to lose his custom react {data['emojis']}")
            try:
                await user.send(embed=discord.Embed(description=f"Your custom react has been deleted because you have no active custom reacts", color=self.bot.default_color))
            except:
                pass
            await self.backend.delete(self.backend.types.reacts, data)
            del self.backend.cach['react'][data['guild_id']][data['user_id']]
            return

        data['max_emoji'] = total_reaction_limit
        data['duration'] = total_duraction

        await self.backend.update(self.backend.types.reacts, data)
        self.backend.cach['react'][data['guild_id']][data['user_id']] = data

    async def highlight_remove_auto(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        user_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, interaction.user.id)
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
        
    privrole = app_commands.Group(name="privrole", description="Manage your custom roles")
    privchannel = app_commands.Group(name="privchannel", description="Manage your custom channels")
    privreact = app_commands.Group(name="privreact", description="Manage your custom reacts")
    highlight = app_commands.Group(name="highlight", description="Manage your custom highlights")
    privemoji = app_commands.Group(name="privemoji", description="Manage your custom emojis")
    perks = app_commands.Group(name="perks", description="Manage your custom perks")
    admin = app_commands.Group(name="admin", description="Manage your custom perks", parent=perks)

    @privrole.command(name="show", description="View your custom roles profile")
    async def _prole(self, interaction: Interaction):
        await interaction.response.send_message("Feching your profile...")
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if not config:
            return await interaction.edit_original_message(content="Server has no custom perks")
        embed = discord.Embed(color=interaction.client.default_color,description="")
        embed.set_author(name=f"{interaction.user}'s Private Roles", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.user.default_avatar)
        user_data = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.edit_original_response(content="You have no custom role use /privrole claim to create one")
        role = interaction.guild.get_role(user_data['role_id'])
        if not role:
            return await interaction.edit_original_response(content="Role not found")
        embed = discord.Embed(color=interaction.client.default_color,description="")
        embed.set_author(name=f"{interaction.user}'s Private Roles", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.user.default_avatar)
        embed.add_field(name=" ", value=f"**Owner**: <@{user_data['user_id']}>\n**Role**: {role.mention}")
        embed.add_field(name=" ", value=f"**Friend Limit**: {user_data['share_limit']}"+ "\n**Friend List:**\n" +"\n".join(
            [f"`{user_data['friend_list'].index(friend) + 1}.` <@{friend}>" for friend in user_data['friend_list']]
        ))
        embed.add_field(name=" ", value=f"**Duration**: {humanfriendly.format_timespan(user_data['duration']) if user_data['duration'] != 'permanent' else 'Permanent'}")
        await interaction.edit_original_response(embed=embed, content=None)

    @privrole.command(name="claim", description="Create a custom role")
    @app_commands.describe(name="name of your custom role", color="color of your custom role like #2b2d31", icon="role icon of your custom role")
    async def _prole_claim(self, interaction: Interaction, name: str, color: str, icon: discord.Attachment=None):
        user_data = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, interaction.user.id)
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if not config:
            return await interaction.response.send_message("Server has no custom perks", ephemeral=True)
        if user_data:
            return await interaction.response.send_message("You already have a custom role use /privrole edit to edit it", ephemeral=True)
        total_duraction = 0
        total_share_limit = 0
        for key, item in config['profiles']['roles'].items():
            role = interaction.guild.get_role(int(key))
            if not role: continue
            if role in interaction.user.roles:

                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']
                if total_share_limit < 10: total_share_limit += item['share_limit']
                elif total_share_limit >= 10: total_share_limit = 10
            
        if total_duraction == 0:
            return await interaction.response.send_message("You have no active custom roles", ephemeral=True)

        await interaction.response.send_message(embed=discord.Embed(description="Creating your custom role...", color=interaction.client.default_color))

        if "AmariMod" in name:
            return await interaction.edit_original_message(content="Role name cannot contain AmariMod", embed=None)
        if len(name) > 100:
            return await interaction.edit_original_message(content="Role name cannot be longer than 30 characters", embed=None)
        
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
        else:
            icon = None
        if "#" not in color:
            return await interaction.edit_original_response(embed=discord.Embed(description="Invalid color make sure to add `#` before the hex code", color=interaction.client.default_color))
        
        color = tuple(round(c*255) for c in Color(color).rgb)
        color = discord.Color.from_rgb(*color)

        position_role = interaction.guild.get_role(config['custom_roles_position'])
        position = position_role.position + 1

        role = await interaction.guild.create_role(name=name, color=color, display_icon=icon)
        await role.edit(position=position)
        user_data = await self.backend.create(self.backend.types.roles, interaction.user.id, interaction.guild.id, duration=total_duraction, share_limit=total_share_limit)
        user_data['role_id'] = role.id
        user_data['created_at'] = datetime.datetime.utcnow()
        await self.backend.update(self.backend.types.roles, user_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Role {role.mention} created successfully", color=interaction.client.default_color))
        await interaction.user.add_roles(role)
    
    @privrole.command(name="edit", description="Edit your custom role")
    @app_commands.checks.cooldown(1, 600, key= lambda i: (i.guild.id, i.user.id))
    @app_commands.describe(name="name of your custom role", color="color of your custom role like #2b2d31", icon="role icon of your custom role")
    async def _prole_edit(self, interaction: Interaction, name: str=None, color: str=None, icon: discord.Attachment=None):
        if name == None and color == None and icon == None:
            return await interaction.response.send_message("You need to provide at least one argument", ephemeral=True)
        user_data = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, interaction.user.id)
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if not config:
            return await interaction.response.send_message("Server has no custom perks", ephemeral=True)
        if not user_data:
            return await interaction.response.send_message("You have no custom role use /privrole claim to create one", ephemeral=True)
        if name:
            if "AmariMod" in name:
                return await interaction.response.send_message(content="Role name cannot contain AmariMod", embed=None)
            if len(name) > 30:
                    return await interaction.response.send_message(content="Role name cannot be longer than 30 characters", embed=None)
        
        if icon:
            if not icon.filename.endswith(("png", "jpg")):
                await interaction.response.send_message(embed=discord.Embed(description="Invalid file type", color=interaction.client.default_color))
                return
            
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message(embed=discord.Embed(description="Failed to download the icon", color=interaction.client.default_color))
                        return

                    icon = await resp.read()
        else:
            icon = None
        if color:
            if "#" not in color:
                return await interaction.response.send_message(embed=discord.Embed(description="Invalid color make sure to add `#` before the hex code", color=interaction.client.default_color))
            color = tuple(round(c*255) for c in Color(color).rgb)
            color = discord.Color.from_rgb(*color)

        role = interaction.guild.get_role(user_data['role_id'])
        if not role:
            return await interaction.response.send_message(content="Role not found", embed=None)
        await interaction.response.send_message(embed=discord.Embed(description="Updating your custom role...", color=interaction.client.default_color))
        keywords = {}
        if name: keywords['name'] = name
        if color: keywords['color'] = color
        if icon: keywords['display_icon'] = icon
        await role.edit(**keywords)

        await interaction.edit_original_response(embed=discord.Embed(description=f"Role {role.mention} updated successfully", color=interaction.client.default_color))
    
    @privrole.command(name="friend", description="Manage your custom role friends")
    async def _prole_friend(self, interaction: Interaction):
        user_data = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom role use /privrole claim to create one", ephemeral=True)
        role = interaction.guild.get_role(user_data['role_id'])
        embed = discord.Embed(title=f"{interaction.user}'s Custom Role Friends", color=interaction.client.default_color if not role.color else role.color, description="")
        embed.description += f"**Friends Limit:** {user_data['share_limit']}\n"
        friends = "".join([f"<@{friend}> `({friend})`\n" for friend in user_data['friend_list']])
        embed.add_field(name="Friends", value=friends if friends else "`No Friends ;(`")
        view = Friends_manage(interaction.user, user_data, "roles")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        return
    
    @privchannel.command(name="show", description="View your custom channel profile")
    async def _pchannel(self, interaction: Interaction):
        embed = discord.Embed(color=interaction.client.default_color,description="")
        embed.set_author(name=f"{interaction.user.name}'s Private channel", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.user.default_avatar)
        user_data = await self.backend.get_data(self.backend.types.channels, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom channel use /privchannel claim to create one", ephemeral=True)
        channel = interaction.guild.get_channel(user_data['channel_id'])
        if not channel:
            return await interaction.response.send_message("Channel not found", ephemeral=True)

        embed.add_field(name=" ", value=f"**Owner**: <@{user_data['user_id']}>\n**Channel**: {channel.mention}")
        embed.add_field(name=" ", value=f"**Friend Limit**: {user_data['share_limit']}"+ "\n**Friend List:**\n" +"\n".join(
            [f"`{user_data['friend_list'].index(friend) + 1}.` <@{friend}>" for friend in user_data['friend_list']]
        ))
        embed.add_field(name=" ", value=f"**Category**: {channel.category.mention}\n**Duration**: {humanfriendly.format_timespan(user_data['duration']) if user_data['duration'] != 'permanent' else 'Permanent'}")

        await interaction.response.send_message(embed=embed, content=None)
    
    @privchannel.command(name="claim", description="Create a custom channel")
    @app_commands.describe(name="name of your custom channel")
    async def _pchannel_claim(self, interaction: Interaction, name: str):
        user_data = await self.backend.channel.find({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if user_data:
            return await interaction.response.send_message("You already have a custom channel use /privchannel edit to edit it", ephemeral=True)
        if not config:
            return await interaction.response.send_message("Server has no custom perks", ephemeral=True)
        
        total_duraction = 0
        total_share_limit = 0
        for key, item in config['profiles']['channels'].items():
            role = interaction.guild.get_role(int(key))
            if not role: continue
            if role in interaction.user.roles:

                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']
                if total_share_limit < 10: total_share_limit += item['share_limit']
                elif total_share_limit >= 10: total_share_limit = 10

        if total_duraction == 0:
            return await interaction.response.send_message("You have no active custom channels", ephemeral=True)
        
        await interaction.response.send_message(embed=discord.Embed(description="Creating your custom channel...", color=interaction.client.default_color))
        category = None
        for cat in config['custom_category']['cat_list']:
            cat = interaction.guild.get_channel(cat)
            if len(cat.channels) < 10:
                category = cat
                break
        if not category:
            last_cat = interaction.guild.get_channel(config['custom_category']['last_cat'])
            category = await interaction.guild.create_category_channel(
                name=f"{config['custom_category']['name']} {len(config['custom_category']['cat_list']) + 1}", 
                position=last_cat.position + 1, overwrites=last_cat.overwrites, reason="Custom Category")
            config['custom_category']['cat_list'].append(category.id)
            config['custom_category']['last_cat'] = category.id
            await self.backend.update(self.backend.types.config, config)
            
        overwrites = category.overwrites
        overwrites[interaction.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True, add_reactions=True)
        overwrites[interaction.guild.me] = discord.PermissionOverwrite(view_channel=True)
        channel = await interaction.guild.create_text_channel(name=name, category=category, topic=f"Private channel of {interaction.user.name}",
                                                              overwrites=overwrites)

        user_data = await self.backend.create(self.backend.types.channels, interaction.user.id, interaction.guild.id, duration=total_duraction, share_limit=total_share_limit)
        user_data['channel_id'] = channel.id
        user_data['created_at'] = datetime.datetime.utcnow()
        await self.backend.update(self.backend.types.channels, user_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Channel {channel.mention} created successfully", color=interaction.client.default_color))
        await channel.send(f"Welcome to your private channel {interaction.user.mention}")
    
    @privchannel.command(name="edit", description="Edit your custom channel")
    @app_commands.checks.cooldown(1, 1200, key= lambda i: (i.guild.id, i.user.id))
    @app_commands.describe(name="name of your custom channel")
    async def _pchannel_edit(self, interaction: Interaction, name: str):
        user_data = await self.backend.get_data(self.backend.types.channels, interaction.guild.id, interaction.user.id)
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if not config:
            return await interaction.response.send_message("Server has no custom perks", ephemeral=True)
        if not user_data:
            return await interaction.response.send_message("You have no custom channel use /privchannel claim to create one", ephemeral=True)
        channel = interaction.guild.get_channel(user_data['channel_id'])
        if not channel:
            return await interaction.edit_original_response(content="Channel not found", embed=None)
        await interaction.response.send_message(embed=discord.Embed(description="Updating your custom channel...", color=interaction.client.default_color))
        await channel.edit(name=name)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Channel {channel.mention} updated successfully", color=interaction.client.default_color))
    
    @privreact.command(name="show", description="View your custom react profile")
    async def _preact(self, interaction: Interaction):
        user_data = await self.backend.get_data(self.backend.types.reacts, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom react use /privreact claim to create one", ephemeral=True)
        
        embed = discord.Embed(color=interaction.client.default_color,description="")
        embed.set_author(name=f"{interaction.user}'s Private Reacts", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.user.default_avatar)
        embed.description += f"**Emojis Limit:** {user_data['max_emoji']}\n"
        embed.add_field(name="Emojis", value=",".join([f"{emoji}" for emoji in user_data['emojis']]))
        await interaction.response.send_message(embed=embed, content=None)
    
    @privchannel.command(name="friend", description="Manage your custom channel friend list")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def _pchannel_friend(self, interaction: Interaction):
        user_data = await self.backend.channel.find({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
        if not user_data:
            return await interaction.response.send_message("You have no custom channel use /privchannel claim to create one", ephemeral=True)
        embed = discord.Embed(title=f"{interaction.user}'s Custom Channel Friends", color=interaction.client.default_color, description="")
        embed.description += f"**Friends Limit:** {user_data['share_limit']}\n"
        friends = "".join([f"<@{friend}> `({friend})`\n" for friend in user_data['friend_list']])
        embed.add_field(name="Friends", value=friends if friends else "`No Friends ;(`")
        view = Friends_manage(interaction.user, user_data, "channels")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
    
    @privreact.command(name="claim", description="Create a custom react")
    @app_commands.describe(emoji="emoji of your custom react")
    async def _preact_claim(self, interaction: Interaction, emoji: str):
        user_data = await self.backend.get_data(self.backend.types.reacts, interaction.guild.id, interaction.user.id)
        if user_data:
            return await interaction.response.send_message("You already have a custom react use /privreact edit to edit it", ephemeral=True)
        
        await interaction.response.send_message(embed=discord.Embed(description="Creating your custom react...", color=interaction.client.default_color))
        config =  await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        total_emojis = 0
        total_duraction = 0

        for key, item in config['profiles']['reacts'].items():
            role = interaction.guild.get_role(int(key))
            if not role: continue
            if role in interaction.user.roles:
                total_emojis += item['share_limit']
                if item['duration'] == "permanent":total_duraction = "permanent"
                else:total_duraction += item['duration']

        if total_emojis >= 10:
            total_emojis == 10

        if total_duraction == 0:
            return await interaction.edit_original_response(embed=discord.Embed(description="You have no active custom reacts", color=interaction.client.default_color))
        else:
            await interaction.edit_original_response(embed=discord.Embed(description=f"Verifying emoji...", color=interaction.client.default_color))

        user_data = await self.backend.create(self.backend.types.reacts, interaction.user.id, interaction.guild.id, duration=total_duraction, share_limit=total_emojis)
        msg = await interaction.original_response()
        try:
            await msg.add_reaction(emoji)
        except:
            return await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji", color=interaction.client.default_color))
        user_data['emojis'].append(emoji)
        user_data['max_emoji'] = total_emojis
        await self.backend.update(self.backend.types.reacts, user_data)
        await self.backend.update_cache(self.backend.types.reacts, interaction.guild, user_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"React {emoji} created successfully", color=interaction.client.default_color))
        await msg.remove_reaction(emoji, interaction.client.user)
    
    @privreact.command(name="edit", description="Edit your custom react")
    @app_commands.checks.cooldown(1, 30, key= lambda i: (i.guild.id, i.user.id))
    async def _preact_edit(self, interaction: Interaction, action: Literal["add", "remove"], emoji: str):
        user_data = await self.backend.get_data(self.backend.types.reacts, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom react use /privreact claim to create one", ephemeral=True)
        if action == "add":
            if len(user_data['emojis']) >= user_data['max_emoji']:
                return await interaction.response.send_message("You have reached the max emoji limit", ephemeral=True)
            
            await interaction.response.send_message(embed=discord.Embed(description="Adding emoji...", color=interaction.client.default_color))
            msg = await interaction.original_response()
            try:await msg.add_reaction(emoji)
            except:return await interaction.edit_original_response(embed=discord.Embed(description="Invalid emoji", color=interaction.client.default_color))

            user_data['emojis'].append(emoji)
            await self.backend.update(self.backend.types.reacts, user_data)
            await self.backend.update_cache(self.backend.types.reacts, interaction.guild, user_data)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Emoji {emoji} added successfully", color=interaction.client.default_color))
        
        elif action == "remove":
            if emoji not in user_data['emojis']:
                return await interaction.response.send_message("Emoji not found", ephemeral=True)
            await interaction.response.send_message(embed=discord.Embed(description="Removing emoji...", color=interaction.client.default_color))
            user_data['emojis'].remove(emoji)
            await self.backend.update(self.backend.types.reacts, user_data)
            await self.backend.update_cache(self.backend.types.reacts, interaction.guild, user_data)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Emoji {emoji} removed successfully", color=interaction.client.default_color))

    @highlight.command(name="tadd", description="add a trigger to your highlight perk")
    @app_commands.describe(trigger="the trigger you want to add")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def highlight_trigger(self, interaction: Interaction, trigger: str):
        user_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, interaction.user.id)
        if not user_data: 
            config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
            if not config: return await interaction.response.send_message("Server has no custom perks", ephemeral=True)
            total_duraction = 0
            total_trigger = 0
            for key, item in config['profiles']['highlights'].items():
                role = interaction.guild.get_role(int(key))
                if not role: continue
                if role in interaction.user.roles:
                    if item['duration'] == "permanent":total_duraction = "permanent"
                    else:total_duraction += item['duration']
                    total_trigger += item['share_limit']
            
            if total_duraction == 0:
                return await interaction.response.send_message("You have no active custom highlights", ephemeral=True)
            user_data = await self.backend.create(self.backend.types.highlights, interaction.user.id, interaction.guild.id, duration=total_duraction, share_limit=total_trigger)

        if len(user_data['triggers']) >= user_data['tigger_limit']: return await interaction.response.send_message("You have reached the maximum amount of triggers", ephemeral=True)      
        if trigger.lower() in user_data['triggers']: return await interaction.response.send_message("You already have that trigger", ephemeral=True)

        user_data['triggers'].append(trigger.lower())
        await self.backend.update(self.backend.types.highlights, user_data)
        await self.backend.update_cache(self.backend.types.highlights, interaction.guild, user_data)

        await interaction.response.send_message(f"Your trigger `{trigger}` has been added", ephemeral=True)
    
    @highlight.command(name="tremove", description="remove a trigger from your highlight perk")
    @app_commands.describe(trigger="the trigger you want to remove")
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.autocomplete(trigger=highlight_remove_auto)
    async def highlight_trigger_remove(self, interaction: Interaction, trigger: str):
        user_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any highlight perks", ephemeral=True)
        if trigger.lower() not in user_data['triggers']: return await interaction.response.send_message("You don't have that trigger", ephemeral=True)

        user_data['triggers'].remove(trigger.lower())
        await self.backend.update(self.backend.types.highlights, user_data)
        await self.backend.update_cache(self.backend.types.highlights, interaction.guild, user_data)

        await interaction.response.send_message(f"Your trigger `{trigger}` has been removed", ephemeral=True)
    
    @highlight.command(name="ignore", description="ignore a user from your highlight perk")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def highlight_ignore_role(self, interaction: Interaction):
        user_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, interaction.user.id)
        if not user_data: return await interaction.response.send_message("You don't have any highlight perks", ephemeral=True)

        embed = discord.Embed(title="Ignore Role/Channel", description="", color=interaction.client.default_color)
        embed.description += "Users:" + f"{', '.join([f'<@{i}>' for i in user_data['ignore_users']]) if user_data['ignore_users'] else '`None`'}"
        embed.description += "\nChannels:" + f"{', '.join([f'<#{i}>' for i in user_data['ignore_channel']]) if user_data['ignore_channel'] else '`None`'}"

        view = Perk_Ignore(user_data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
    
    @highlight.command(name="show", description="View your custom highlight profile")
    async def _highlight_show(self, interaction: Interaction):
        user_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom highlight use /highlight tadd to create one", ephemeral=True)
        
        embed = discord.Embed(color=interaction.client.default_color,description="")
        formated_args = await get_formated_embed(["Triggers Limit", "Triggers", "Ignore Users", "Ignore Channels"])
        embed.description += f"**Triggers Limit:** {user_data['tigger_limit']}\n"
        embed.description += f"{formated_args['Triggers']}{', '.join(user_data['triggers']) if len(user_data['triggers']) > 0 else 'None'}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Ignore Users'], data=user_data['ignore_users'], type='user')}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Ignore Channels'], data=user_data['ignore_channel'], type='channel')}"

        await interaction.response.send_message(embed=embed, content=None)

    @privemoji.command(name="show", description="View your custom emoji profile")
    async def _pemoji(self, interaction: Interaction):
        user_data = await self.backend.get_data(self.backend.types.emojis, interaction.guild.id, interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("You have no custom emoji use /privemoji claim to create one", ephemeral=True)
        
        emojis = []
        for emoji in user_data['emojis']:
            emoji = interaction.guild.get_emoji(emoji)
            if emoji: emojis.append(str(emoji))

        embed = discord.Embed(color=interaction.client.default_color,description="")
        formated_args = await get_formated_embed(["Max Emojis", "Emojis"])
        embed.description = ""
        embed.description += f"`{interaction.user.name}`'s Custom Emojis\n\n"
        embed.description += f"{formated_args['Max Emojis']}{user_data['max_emoji']}\n"
        embed.description += f"{formated_args['Emojis']}{', '.join(emojis) if len(emojis) > 0 else 'None'}"
        await interaction.response.send_message(embed=embed, content=None)

    @privemoji.command(name="claim", description="Create a custom emoji")
    @app_commands.describe(emoji="emoji of your custom emoji", name="name of your custom emoji")
    async def _pemoji_claim(self, interaction: Interaction, emoji: discord.Attachment, name: app_commands.Range[str, 1, 20]):
        await interaction.response.send_message(embed=discord.Embed(description="Processing your request...", color=interaction.client.default_color))

        user_profile_info = await self.backend.calulate_profile(self.backend.types.emojis, interaction.guild, interaction.user)
        if user_profile_info['duration'] == 0:
            return await interaction.edit_original_response(content=None, embed=discord.Embed(description="You have no active custom emojis", color=interaction.client.default_color))

        already_requested = await self.backend.emoji_request.find({"guild_id": interaction.guild.id, "user_id": interaction.user.id})
        if already_requested:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description="You already have a pending request for a custom emoji please wait for the admin to respond", color=interaction.client.default_color))
            return

        filename = emoji.filename
        if not emoji.filename.endswith(("jpg", "png","gif")):
            return await interaction.edit_original_response(content=None, embed=discord.Embed(description="Invalid file type", color=interaction.client.default_color))
        
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji.url) as resp:
                if resp.status != 200:
                    return await interaction.edit_original_response(content=None, embed=discord.Embed(description="Failed to download the emoji", color=interaction.client.default_color))
                emoji = await resp.read()
                await session.close()
        
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if not config: return await interaction.edit_original_response(content=None, embed=discord.Embed(description="Server has no custom perks", color=interaction.client.default_color))

        all_emojis = await self.backend.emoji.find_many_by_custom({"guild_id": interaction.guild.id})
        print(all_emojis)
        if len(all_emojis) >= config['emojis']['max']:
            return await interaction.edit_original_response(content=None, embed=discord.Embed(description="Server has reached the max emoji limit", color=interaction.client.default_color))
        
        emoji_reqeust_channel = interaction.guild.get_channel(config["emojis"]['request_channel'])
        if not emoji_reqeust_channel:
            return await interaction.edit_original_response(content=None, embed=discord.Embed(description="Emoji request channel not found", color=interaction.client.default_color))

        
        fromated_args = await get_formated_embed(["User", "Name"])
        embed = discord.Embed(color=interaction.client.default_color, description="")
        embed.description = ""
        embed.description += "<:tgk_bid:1114854528018284595> `Emoji Request`\n\n"
        embed.description += f"{fromated_args['User']}{interaction.user.mention}\n"
        embed.description += f"{fromated_args['Name']}{name}\n\n"
        embed.description += f"<:tgk_hint:1206282482744561744> Use below buttons to accept or reject the request"

        file = discord.File(fp=io.BytesIO(emoji), spoiler=False, filename=filename)
        req_message = await emoji_reqeust_channel.send(content=None, embed=embed, file=file, view=Emoji_Request())
        
        await interaction.edit_original_response(content=None, embed=discord.Embed(description="Your request has been sent to the admins", color=interaction.client.default_color))

        emmoji_request_data = {
            "_id": req_message.id,
            "user_id": interaction.user.id,
            "guild_id": interaction.guild.id,
            "name": name,
        }
        await self.backend.emoji_request.insert(emmoji_request_data)

    @admin.command(name="premove", description="remove a custom perk from a user")
    @app_commands.describe(member="The member you want to manage", perk="The perk you want to manage")
    async def _premove(self, interaction: Interaction, member: discord.Member, perk: Perk_Type):

        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
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
        
        if perk == self.backend.types.config:
            await interaction.response.send_message("You can't remove config", ephemeral=True)
            return
        perk_data = await self.backend.get_data(perk, interaction.guild.id, member.id)
        if not perk_data:
            await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
            return
        await self.backend.delete(perk, perk_data)
        await interaction.response.send_message(f"Successfully removed {perk.name} from {member.mention}", ephemeral=False)

        if perk == self.backend.types.channels:
            channel = interaction.guild.get_channel(perk_data['channel_id'])
            if channel: await channel.delete(reason=f"Perk Removed By {interaction.user.name}")
        
        if perk == self.backend.types.roles:
            role = interaction.guild.get_role(perk_data['role_id'])
            if role: await role.delete(reason=f"Perk Removed By {interaction.user.name}")
        
        if perk == self.backend.types.reacts:
            try: del self.backend.cach['react'][interaction.guild.id][member.id]
            except: pass
            try: self.backend.cach['react'][interaction.guild.id].pop(member.id)
            except:pass
        
        if perk == self.backend.types.highlights:
            try: del self.backend.cach['highlight'][interaction.guild.id][member.id]
            except: pass
            try: self.backend.cach['highlight'][interaction.guild.id].pop(member.id)
            except:pass

    @admin.command(name="psearch", description="find the owner of a custom perk")
    @app_commands.describe(role="The role you want to search for", channel="The channel you want to search for")
    async def _psearch(self, interaction: Interaction,role: discord.Role=None, channel: discord.TextChannel=None):
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return
        if role is None and channel is None: return await interaction.response.send_message("You need to specify a role or a channel", ephemeral=True)
        embeds = []
        if role:
            role_data = await self.backend.roles.find({"role_id": role.id, "guild_id": interaction.guild.id})
            if not role_data: return await interaction.response.send_message("No results found", ephemeral=True)
            user_data = interaction.guild.get_member(role_data['user_id'])
            duration = humanfriendly.format_timespan(role_data['duration']) if role_data['duration'] != "permanent" else "Permanent"
            role_embed = discord.Embed(title="Custom Role Info", color=interaction.client.default_color, description="")
            role_embed.description += f"**User:** {user_data.mention}\n"
            role_embed.description += f"**Role:** {role.mention}\n"
            role_embed.description += f"**Duration:** {duration}\n"
            role_embed.description += f"**Friend Limit:** {role_data['share_limit']}\n"
            role_embed.description += f"**Friends:**" + ", ".join([f"<@{friend}>" for friend in role_data['friend_list']]) if len(role_data['friend_list']) > 0 else "None"
            embeds.append(role_embed)
        if channel:
            channel_data = await self.backend.channel.find({"channel_id": channel.id, "guild_id": interaction.guild.id})
            if not channel_data: return await interaction.response.send_message("No results found", ephemeral=True)
            user_data = interaction.guild.get_member(channel_data['user_id'])
            duration = humanfriendly.format_timespan(channel_data['duration']) if channel_data['duration'] != "permanent" else "Permanent"
            channel_embed = discord.Embed(title="Custom Channel Info", color=interaction.client.default_color, description="")
            channel_embed.description += f"**User:** {user_data.mention}\n"
            channel_embed.description += f"**Channel:** {channel.mention}\n"
            channel_embed.description += f"**Duration:** {duration}\n"
            channel_embed.description += f"**Friend Limit:** {channel_data['share_limit']}\n"
            channel_embed.description += f"**Friends:**" + ", ".join([f"<@{friend}>" for friend in channel_data['friend_list']]) if len(channel_data['friend_list']) > 0 else "None"
            channel_embed.add_field(name="Activiy", value=f"**Rank: **{channel_data['activity']['rank']}\n**Messages:** {channel_data['activity']['messages']}\n")
            embeds.append(channel_embed)
        if len(embeds) == 0: return await interaction.response.send_message("No results found", ephemeral=True)
        await interaction.response.send_message(embeds=embeds)

    @admin.command(name="block", description="block a user from using custom perks")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(member="The member you want to block", reason="The reason of the block")
    async def _ban(self, interaction: Interaction, member: discord.Member, reason: str):
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return

        ban_data = {
            "user_id": member.id,
            "guild_id": interaction.guild.id,
            "reason": reason,
            "banned_by": interaction.user.id
        }
        await self.backend.bans.insert(ban_data)
        await interaction.response.send_message(f"{member.mention} has been blocked from using custom perks clearing all their perks this may take few seconds", ephemeral=True)
        role_data = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, member.id)
        channel_data = await self.backend.get_data(self.backend.types.channels, interaction.guild.id, member.id)
        react_data = await self.backend.get_data(self.backend.types.reacts, interaction.guild.id, member.id)
        highlight_data = await self.backend.get_data(self.backend.types.highlights, interaction.guild.id, member.id)

        if role_data: 
            role = interaction.guild.get_role(role_data['role_id'])
            if role: await role.delete(reason=f"Perk Owner blocked by {interaction.user.name}")
            await self.backend.delete(self.backend.types.roles, role_data)
        if channel_data:
            channel = interaction.guild.get_channel(channel_data['channel_id'])
            if channel: await channel.delete(reason=f"Perk Owner blocked by {interaction.user.name}")
            await self.backend.delete(self.backend.types.channels, channel_data)
        if react_data:
            self.backend.cach['react'][interaction.guild.id].pop(member.id)
            await self.backend.delete(self.backend.types.reacts, react_data)
            try: del self.backend.cach['react'][interaction.guild.id][member.id]
            except: pass
        if highlight_data:
            self.backend.cach['highlight'][interaction.guild.id].pop(member.id)
            await self.backend.delete(self.backend.types.highlights, highlight_data)
            try:del self.backend.cach['highlight'][interaction.guild.id][member.id]
            except: pass
        
        await interaction.followup.send(f"All existing perks of {member.mention} has been cleared successfully", ephemeral=True)

    
    @admin.command(name="unblock", description="unblock a user from using custom perks")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(member="The member you want to unblock")
    async def _unban(self, interaction: Interaction, member: discord.Member):
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():

            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return
        ban_data = await self.backend.bans.find({"user_id": member.id, "guild_id": interaction.guild.id})
        if not ban_data:
            await interaction.response.send_message("This user is not blocked", ephemeral=True)
            return
        await self.backend.bans.delete(ban_data)
        await interaction.response.send_message(f"{member.mention} has been unblocked from using custom perks", ephemeral=True)

    @admin.command(name="freez", description="Freez a custom perk's share limit/deletion")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(member="The member you want to freez", perk="The perk you want to freez", type='which attribute you want to freez', value="The value you want to set")
    async def _freez(self, interaction: Interaction, member: discord.Member, perk: Literal["roles", "channel"], type: Literal["share", "delete"], value: bool):
        config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return
        match perk:
            case "roles":
                perk_data: Custom_Roles = await self.backend.get_data(self.backend.types.roles, interaction.guild.id, member.id)
            case "channel":
                perk_data: Custom_Channel = await self.backend.get_data(self.backend.types.channels, interaction.guild.id, member.id)
            case _:
                await interaction.response.send_message("Invalid perk", ephemeral=True)

        if not perk_data:
            await interaction.response.send_message("This user doesn't have this perk", ephemeral=True)
            return
        if type == "share":
            perk_data['freeze']['share_limit'] = value
        if type == "delete":
            perk_data['freeze']['delete'] = value
        await self.backend.update(perk, perk_data)
        await interaction.response.send_message(f"Successfully updated {member.mention}'s {perk} {type} freeze to {value}", ephemeral=True)


    @admin.command(name="sync-top-cat", description="sync top category with all channels")
    @app_commands.default_permissions(administrator=True)
    async def _sync_top_cat(self, interaction: Interaction):
        config: Config = await self.backend.get_data(self.backend.types.config, interaction.guild.id, interaction.user.id)
        if config == None:
            await interaction.response.send_message("You need to setup config first", ephemeral=True)
            return
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['admin_roles'])) == set():
            await interaction.response.send_message("You need to have admin roles to use this command", ephemeral=True)
            return
        top_cat = interaction.guild.get_channel(config['top_channel_category']['cat_id'])
        if not top_cat:
            await interaction.response.send_message("Top category not found", ephemeral=True)
            return

        await interaction.response.send_message("Syncing all channels with the top category")

        top_roles = []
        for profile in config['profiles']['channels'].keys():
            profile: Profile = config['profiles']['channels'][profile]
            if profile['top_profile']:
                role = interaction.guild.get_role(profile['role_id'])
                if role: top_roles.append(role)
        
        for chl in await self.backend.channel.find_many_by_custom({"guild_id": interaction.guild.id}):
            chl: Custom_Channel
            channel = interaction.guild.get_channel(chl['channel_id'])
            owner = interaction.guild.get_member(chl['user_id'])
            if not channel: 
                await self.backend.delete(self.backend.types.channels, chl)
                continue
            
            if (set(owner.roles) & set(top_roles)) == set():
                if channel.category != top_cat:pass
                else:
                    await channel.edit(category=interaction.guild.get_channel(chl['activity']['previous_cat']))
            else:
                if channel.category == top_cat:pass
                else:
                    chl['activity']['previous_cat'] = channel.category.id
                    await self.backend.update(self.backend.types.channels, chl)
                    await channel.edit(category=top_cat)
        await interaction.edit_original_response(content="All channels has been synced with the top category")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:             
            return
        if message.guild is None: return
        if len(message.mentions) > 0:
            self.bot.dispatch('auto_react', message)
        if message.content is not None or message.content != "":
            self.bot.dispatch('auto_highlight', message)
        
        custom_channel: Custom_Channel  = await self.backend.channel.find({"channel_id": message.channel.id, "guild_id": message.guild.id})
        if not custom_channel: return
        if message.author.id == custom_channel['user_id']: return
        if 'last_message' not in custom_channel['activity'].keys():
            custom_channel['activity']['last_message'] = None
        if custom_channel['activity']['last_message'] is not None:
            if not datetime.datetime.utcnow() > custom_channel['activity']['last_message'] + datetime.timedelta(seconds=8):
                return
        custom_channel['activity']['messages'] += 1
        custom_channel['activity']['last_message'] = datetime.datetime.utcnow()
        await self.backend.update(self.backend.types.channels, custom_channel)
        return

    @commands.Cog.listener()
    async def on_auto_highlight(self, message: discord.Message):
        if message.guild.id not in self.backend.cach['highlight'].keys(): return
        guild_data = self.backend.cach['highlight'][message.guild.id]
        message_content = message.content.lower()
        message_content = message_content.split(" ")
        trigger_users = []
        for word in message_content:
            for user_data in guild_data:
                word = str(word)
                user_data = guild_data[user_data]
                if word in user_data['triggers']:
                    user = message.guild.get_member(user_data['user_id'])
                    if message.author.id == user_data['user_id']: continue
                    if user is None: continue
                    perm = message.channel.permissions_for(user)
                    if not perm.view_channel or perm.view_channel == False: continue
                    if user in trigger_users: 
                        continue
                    trigger_users.append(user)
                    self.bot.dispatch('highlight_found', message, user_data)
                    continue


    @commands.Cog.listener()
    async def on_highlight_found(self, message: discord.Message, user_data: dict):
        now = datetime.datetime.utcnow()
        user = message.guild.get_member(user_data['user_id'])

        if user_data['last_trigger'] is not None:
            if not now > user_data['last_trigger'] + datetime.timedelta(minutes=1):
                return
        
        if message.channel.id in user_data['ignore_channel'] or message.author.id in user_data['ignore_users']:
            return

        before_messages = [message async for message in message.channel.history(limit=10, before=message)]

        embed = discord.Embed(title=f"Hightlight found in {message.guild.name}", color=self.bot.default_color, description="")
        before_messages.reverse()
        for bmessage in before_messages:
            if bmessage.id == user_data['user_id']:
                if not now > message.created_at + datetime.timedelta(minutes=5): 
                    return
                pass
            
            embed.description += f"**[<t:{round(bmessage.created_at.timestamp())}:T>] {bmessage.author.display_name}:** {bmessage.content}\n"        
        embed.add_field(name="Trigger Message", value=f"[<t:{round(message.created_at.timestamp())}:T>] {message.author.display_name}: {message.content}", inline=False)
        embed.set_footer(text=f"Triggered by {message.author.global_name}", icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar)
        try:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", url=message.jump_url, style=discord.ButtonStyle.url, emoji="<:tgk_link:1105189183523401828>"))
            await user.send(embed=embed, view=view)
        except:
            pass
        user_data['last_trigger'] = datetime.datetime.utcnow()
        await self.backend.update_cache(self.backend.types.highlights, message.guild, user_data)
        await self.backend.update(self.backend.types.highlights, user_data)

    @commands.Cog.listener()
    async def on_auto_react(self, message: discord.Message):
        if len(message.mentions) == 0: return
        if message.guild.id not in self.backend.cach['react'].keys(): return
        guild_data = self.backend.cach['react'][message.guild.id]
        now = datetime.datetime.utcnow()
        for mention in message.mentions:
            if mention.id in guild_data.keys():
                user_data = guild_data[mention.id]
                if user_data['last_react'] is None:
                    try:
                        await message.add_reaction(random.choice(user_data['emojis']))
                    except:
                        continue
                    user_data['last_react'] = datetime.datetime.utcnow()
                    await self.backend.update_cache(self.backend.types.reacts, message.guild, user_data)
                else:
                    if now > user_data['last_react'] + datetime.timedelta(seconds=5):
                        try:
                            await message.add_reaction(random.choice(user_data['emojis']))
                        except Exception as e:
                            continue
                        user_data['last_react'] = datetime.datetime.utcnow()
                        await self.backend.update_cache(self.backend.types.reacts, message.guild, user_data)

async def setup(bot):
    await bot.add_cog(Perks(bot))
