import discord
import datetime
import re

from discord import app_commands
from discord.ext import commands, tasks
from utils.transformer import TimeConverter
from humanfriendly import format_timespan
from utils.db import Document
from copy import deepcopy

emojis ={
    'timeout': "<:octane_timeout:1064170126208925696>",
    'ban': "<:octane_ban:1064170126208925696>",
    'kick': "<:octane_kick:1064170126208925696>",
    'mute': "<:octane_mute:1064184628476391505>",
    'unmute': "<:octane_unmute:1064170126208925696>",
    'unban': "<:octane_unban:1064185537872801812>",
}

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.mod_config = Document(bot.db, "mod_config") 
    
    async def setup_mute(self, guild: discord.Guild):
        muted_role = await guild.create_role(name="Muted", reason="Muted role for Octane")
        muted_role.edit(position=guild.me.top_role.position - 1)
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, add_reactions=False, view_channel=False)
        return muted_role
    
    def send_mod_log(self, moderator: discord.Member, member: discord.Member, reason: str, action: str, case: int, duration: int=None, color: discord.Color=discord.Color.red()):
        embed = discord.Embed(
            title=f"{emojis[action.lower()]} {action} | Case #{case}",
            description=f"**Member:** {member.mention} ({member.id})\n**Moderator:** {moderator.mention} ({moderator.id})\n**Reason:** {reason}"
            )
        if duration: embed.description += f"\n**Duration:** {format_timespan(duration)}"
        return embed
    
    async def check_hierarchy(self, interaction: discord.Interaction, moderator: discord.Member, member: discord.Member):
        if moderator.top_role.position <= member.top_role.position:
            embed = discord.Embed(description=f"<:octane_no:1019957051721535618> | You cannot {interaction.command.name} this member due to role hierarchy", color=discord.Color.red())
            interaction.response.send_message(embed=embed)
            return True

        if moderator.id == member.id:
            embed = discord.Embed(description=f"<:octane_no:1019957051721535618> | You cannot {interaction.command.name} yourself", color=discord.Color.red())
            interaction.response.send_message(embed=embed)
            return True
        
        if moderator.guild.owner_id == member.id:
            embed = discord.Embed(description=f"<:octane_no:1019957051721535618> | You cannot {interaction.command.name} the server owner", color=discord.Color.red())
            interaction.response.send_message(embed=embed)
            return True
        
        if member.bot or member == interaction.guild.me:
            embed = discord.Embed(description=f"<:octane_no:1019957051721535618> | You cannot {interaction.command.name} a bot", color=discord.Color.red())
            interaction.response.send_message(embed=embed)
            return True

        if interaction.guild.me.top_role <= member.top_role:
            embed = discord.Embed(description=f"<:octane_no:1019957051721535618> | I cannot {interaction.command.name} this member due to role hierarchy", color=discord.Color.red())
            interaction.response.send_message(embed=embed)
            return True

        return False

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(user="The user to timeout", reason="The reason for the timeout and duration")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: app_commands.Transform[str, TimeConverter]=3600):
        try:
            await user.send(f"You have been timeout for {reason} for {format_timespan(duration)}")
        except discord.HTTPException:
            pass

        await user.edit(timed_out_until=discord.utils.utcnow() + datetime.timedelta(seconds=duration))
        embed = discord.Embed(description=f"<:octane_yes:1019957051721535618> | {user.mention} has been timeout for {reason} for {format_timespan(duration)}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

        log_data = await self.bot.mod_config.find(interaction.guild.id)
        if log_data is None:
            log_data = {"_id": interaction.guild.id, "mod_log": None, 'case': 0}
            await self.bot.mod_config.insert(log_data)
        
        log_channel = interaction.guild.get_channel(log_data["mod_log"])
        if log_channel is None:return
        embed = self.send_mod_log(interaction.user, user, reason, "Timeout", log_data["case"], duration, discord.Color.green())
        await log_channel.send(embed=embed)
        log_data["case"] += 1
        await self.bot.mod_config.update(log_data)
    
    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="The user to ban", reason="The reason for the ban", duration="The duration for the ban")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: app_commands.Transform[str, TimeConverter]="Permanent"):

        if self.check_hierarchy(interaction, interaction.user, user): return

        try:
            await user.send(f"You have been banned for {reason} for {format_timespan(duration) if duration != 'Permanent' else 'Permanently'}")
        except discord.HTTPException:
            pass

        await user.ban(reason=reason)
        embed = discord.Embed(description=f"<:octane_yes:1019957051721535618> | {user.mention} has been banned for {reason}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

        log_data = await self.bot.mod_config.find(interaction.guild.id)
        if log_data is None:
            log_data = {"_id": interaction.guild.id, "mod_log": None, 'case': 0}
            await self.bot.mod_config.insert(log_data)
        
        log_channel = interaction.guild.get_channel(log_data["mod_log"])
        if log_channel is None:return
        embed = self.send_mod_log(interaction.user, user, reason, "Ban", log_data["case"], duration, discord.Color.green())
        await log_channel.send(embed=embed)
        log_data["case"] += 1
        await self.bot.mod_config.update(log_data)

        if duration != "Permanent":
            ban_data = {
                "_id": user.id,
                "guild": interaction.guild.id,
                "reason": reason,
                "duration": duration,
                "moderator": interaction.user.id,
                "banned_at": datetime.datetime.utcnow(),
            }
            await self.bot.ban.insert(ban_data)
            self.bot.bans[user.id] = ban_data

    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="Id of the user to unban", reason="The reason for the unban")
    async def unban(self, interaction: discord.Interaction, user: str, reason: str):
        user = await self.bot.fetch_user(user)
        try:
            ban = await interaction.guild.fetch_ban(user)
        except discord.NotFound:
            return await interaction.response.send_message("User is not banned", ephemeral=True)
        await interaction.guild.unban(user, reason=reason)
        embed = discord.Embed(description=f"<:octane_yes:1019957051721535618> | {user.mention} has been unbanned for {reason}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
        try:
            self.bot.bans.pop(user.id)
        except KeyError:
            pass
        await self.bot.ban.delete(user.id)
    
    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(user="The user to mute", reason="The reason for the mute", duration="The duration for the mute")
    async def mute(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: app_commands.Transform[str, TimeConverter]="Permanent"):
        
        if self.check_hierarchy(interaction, interaction.user, user): return

        roles, old_roles = [], []      
        for r in user.roles:
            if r == interaction.guild.default_role or r.managed or r.position >= interaction.guild.me.top_role.position or r.name == "Muted": 
                roles.append(r)
            else:
                old_roles.append(r.id)
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if mute_role is None:
            mute_role = await self.setup_mute(interaction.guild)

        roles.append(mute_role)
        await user.edit(roles=roles, reason=reason)

        embed = discord.Embed(description=f"<:octane_yes:1019957051721535618> | {user.mention} has been muted for {reason}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

        log_data = await self.bot.mod_config.find(interaction.guild.id)
        if log_data is None:
            log_data = {"_id": interaction.guild.id, "mod_log": None, 'case': 0}
            await self.bot.mod_config.insert(log_data)
        
        log_channel = interaction.guild.get_channel(log_data["mod_log"])
        if log_channel is None:return
        embed = self.send_mod_log(interaction.user, user, reason, "Mute", log_data["case"], duration, discord.Color.green())
        await log_channel.send(embed=embed)
        log_data["case"] += 1
        await self.bot.mod_config.update(log_data)

        if duration != "Permanent":
            mute_data = {
                "_id": user.id,
                "guild": interaction.guild.id,
                "reason": reason,
                "duration": duration,
                "moderator": interaction.user.id,
                "muted_at": datetime.datetime.utcnow(),
                "roles": old_roles
            }
            await self.bot.mute.upsert(mute_data)
            self.bot.mutes[user.id] = mute_data
    
class Moderation_Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.mutes = {}
        self.bot.bans = {}
        self.bot.ban = Document(self.bot.db, "bans")
        self.bot.mute = Document(self.bot.db, "mutes")
        self.bot.bans_task_running = False
        self.bot.mutes_task_running = False
        self.bot.mute_task = self.check_mutes.start()
        self.bot.ban_task = self.check_bans.start()
    
    def cog_unload(self):
        self.bot.mute_task.cancel()
        self.bot.ban_task.cancel()
    
    def send_mod_log(self, moderator: discord.Member, member: discord.Member, reason: str, action: str, case: int, duration: int=None, color: discord.Color=discord.Color.red()):
        embed = discord.Embed(
            title=f"{emojis[action.lower()]} {action} | Case #{case}",
            description=f"**Member:** {member.mention} ({member.id})\n**Moderator:** {moderator.mention} ({moderator.id})\n**Reason:** {reason}"
            )
        if duration: embed.description += f"\n**Duration:** {format_timespan(duration)}"
        return embed
    
    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @tasks.loop(seconds=10)
    async def check_bans(self):
        if self.bot.bans_task_running:
            return
        self.bot.bans_task_running = True
        current_mutes = deepcopy(self.bot.bans)
        current_time = datetime.datetime.utcnow()
        for user_id, mute in current_mutes.items():
            if current_mutes >= mute['banned_at'] + datetime.timedelta(seconds=mute['duration']):
                #dispatch event
                pass
        self.bot.bans_task_running = False
    
    @tasks.loop(seconds=10)
    async def check_mutes(self):
        if self.bot.mutes_task_running:
            return
        self.bot.mutes_task_running = True
        current_mutes = deepcopy(self.bot.mutes)
        current_time = datetime.datetime.utcnow()
        for user_id, mute in current_mutes.items():
            if current_mutes >= mute['muted_at'] + datetime.timedelta(seconds=mute['duration']):
                #dispatch event
                pass
        self.bot.mutes_task_running = False
    
    @commands.Cog.listener()
    async def on_unban(self, data: dict):
        data = await self.bot.ban.find(data['_id'])
        if data is None: return
        
        guild = self.bot.get_guild(data['guild'])
        user = guild.get_member(data['_id'])
        try:
            ban = await guild.fetch_ban(user)
        except discord.NotFound:
            return

        await guild.unban(user, reason=data['reason'])

        log_data = await self.bot.mod_config.find(guild.id)
        if log_data is None:
            log_data = {"_id": guild.id, "mod_log": None, 'case': 0}
            await self.bot.mod_config.insert(log_data)

        log_channel = guild.get_channel(log_data["mod_log"])
        if log_channel is None:return
        embed = self.send_mod_log(guild.get_member(data['moderator']), user, data['reason'], "Unban", log_data["case"], discord.Color.green())
        await log_channel.send(embed=embed)
        log_data["case"] += 1
        await self.bot.mod_config.update(log_data)

        await self.bot.ban.delete(data['_id'])
        try:
            self.bot.bans.pop(data['_id'])
        except KeyError:
            pass
    
    @commands.Cog.listener()
    async def on_unmute(self, data: dict):
        if self.bot.mute_task_running: return
        self.bot.mute_task_running = True

        data = await self.bot.mute.find(data['_id'])
        if data is None: return
        
        guild = self.bot.get_guild(data['guild'])
        user = guild.get_member(data['_id'])
        mod = guild.get_member(data['moderator'])
        if user is None: 
            data['muted_at'] = datetime.datetime.utcnow()
            await self.bot.mute.upsert(data)
            return
        
        muted = discord.utils.get(user.roles, name="Muted")
        await user.remove_roles(muted, reason=f"Automatic unmute expired made by {format_timespan(data['duration'])} ago")
        roles = [guild.get_role(role_id) for role_id in data['roles']]
        await user.edit(roles=roles, reason=f"Automatic unmute expired made by {format_timespan(data['duration'])} ago")

        log_data = await self.bot.mod_config.find(guild.id)
        if log_data is None:
            log_data = {"_id": guild.id, "mod_log": None, 'case': 0}
            await self.bot.mod_config.insert(log_data)
        
        log_channel = guild.get_channel(log_data["mod_log"])
        if log_channel is None:return
        embed = self.send_mod_log(mod, user, data['reason'], "Unmute", log_data["case"], discord.Color.green())
        await log_channel.send(embed=embed)
        log_data["case"] += 1
        await self.bot.mod_config.update(log_data)

        await self.bot.mute.delete(data['_id'])
        try:
            self.bot.mutes.pop(data['_id'])
        except KeyError:
            pass
        self.bot.mute_task_running = False
    
    @check_bans.before_loop
    async def before_check_bans(self):
        await self.bot.wait_until_ready()
    
    @check_mutes.before_loop
    async def before_check_mutes(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(Moderation_Tasks(bot))