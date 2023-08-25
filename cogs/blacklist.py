from dataclasses import dataclass, asdict, field
from discord.ext import commands, tasks
from discord import app_commands
from utils.db import Document
from utils.paginator import Paginator
from typing import List, Dict
from utils.transformer import TimeConverter
from humanfriendly import format_timespan
import datetime
import discord

@dataclass
class Profile:
    _id: str
    create_by: int
    create_at: datetime.datetime
    role_add: List[int]
    role_remove: List[int]
    reason: str = "No reason provided"

    def to_dict(self):
        return asdict(self)

@dataclass
class Config:
    _id: int
    mod_roles: List[int]
    profiles: Dict[str, Profile]
    log_channel: int

    def to_dict(self):
        return asdict(self)

@dataclass
class Blacklist:
    user_id: int
    guild_id: int
    profile: str
    Blacklist_at: datetime.datetime
    Blacklist_by: int
    Blacklist_reason: str
    Blacklist_duration: int
    Blacklist_end: datetime.datetime

    def to_dict(self):
        return asdict(self)

class backend:
    def __init__(self, bot):
        self.db = bot.mongo["Blacklist"]
        self.config = Document(self.db, "config")
        self.blacklist = Document(self.db, "blacklist")
        self.config_cache: Dict[Dict] = {}

    async def setup(self):
        for guild in await self.config.get_all():
            self.config_cache[guild["_id"]] = Config(**guild)
    
    async def create_config(self, guild_id: int) -> Config:
        config = Config(guild_id, [], {}, None)
        config = await self.config.insert(config.to_dict())
        self.config_cache[guild_id] = config
        return Config(**config)
    
    async def get_config(self, guild_id: int) -> Config:
        if guild_id in self.config_cache.keys():
            return self.config_cache[guild_id]
        else:
            data = await self.config.find(guild_id)
            if data is None:
                return await self.create_config(guild_id)
            else:
                return Config(**data)
    
    async def update_config(self, guild_id: int, data: Config | dict ):
        if isinstance(data, dict):
            data = Config(**data)
        await self.config.update(guild_id, data.to_dict())
        self.config_cache[guild_id] = data
    
    async def get_blacklist(self, user: discord.Member, profile: Profile) -> Blacklist:
        data = await self.blacklist.find({"user_id": user.id, "profile": profile._id, "guild_id": user.guild.id})
        if not data:
            return None
        del data["_id"]
        return Blacklist(**data)

    async def insert_blacklist(self, data: Blacklist):
        await self.blacklist.insert(data.to_dict())
    

class Blacklist_cog(commands.GroupCog, name="blacklist"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = backend(bot)
        self.bot.blacklist = self.backend
        self.unblacklist_task = self.unblacklist.start()
        self.unbl_task = False
    
    user = app_commands.Group(name="user", description="Blacklist user")

    def cog_unload(self):
        self.unblacklist_task.cancel()
    
    async def profile_aucto(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        config = await self.backend.get_config(interaction.guild_id)
        profiles: List[str] = [profile for profile in config.profiles.keys()]
        choices = [
            app_commands.Choice(name=profile, value=profile) 
            for profile in profiles if current.lower() in profile.lower()
        ]
        return choices[:24]

    @tasks.loop(minutes=1)
    async def unblacklist(self):
        if self.unbl_task: return
        self.unbl_task = True
        now = datetime.datetime.utcnow()
        data = await self.backend.blacklist.get_all()
        for blacklist in data:
            if blacklist["Blacklist_end"] < now:
                guild = self.bot.get_guild(blacklist["guild_id"])
                user = guild.get_member(blacklist["user_id"])
                if not user:
                    blacklist["Blacklist_end"] = now + blacklist["Blacklist_duration"]
                    await self.backend.blacklist.update(blacklist)
                    continue
                self.bot.dispatch("blacklist_remove", blacklist)
            else:
                continue
        self.unbl_task = False
    
    @unblacklist.before_loop
    async def before_unblacklist(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_blacklist_remove(self, blacklist:dict):
        guild = self.bot.get_guild(blacklist["guild_id"])
        user = guild.get_member(blacklist["user_id"])
        config = await self.backend.get_config(guild.id)
        profile = Profile(**config.profiles[blacklist["profile"]])
        role_remove = [guild.get_role(role) for role in profile.role_add]
        role_add = [guild.get_role(role) for role in profile.role_remove]
        await user.remove_roles(*role_remove, reason="Blacklist expired")
        await user.add_roles(*role_add, reason="Blacklist expired")

        if config.log_channel:
            channel = guild.get_channel(config.log_channel)
            embed = discord.Embed(title="Blacklist expired", color=self.bot.default_color, description="")
            embed.description += f"**User:** {user.mention} ({user.id})\n"
            embed.description += f"**Profile:** {profile._id}\n"
            embed.description += f"**Reason:** {blacklist['Blacklist_reason']}\n"
            embed.description += f"**By:** <@{blacklist['Blacklist_by']}> ({blacklist['Blacklist_by']})\n"

            await channel.send(embed=embed)
        await self.backend.blacklist.delete({"user_id": user.id, "profile": profile._id, "guild_id": guild.id})

    @commands.Cog.listener()
    async def on_ready(self):
        await self.backend.setup()
    
    @user.command(name="add", description="apply blacklist to user")
    @app_commands.describe(profile="Profile to apply blacklist", user="User to blacklist", reason="Reason for blacklist", duration="Duration of blacklist")
    @app_commands.autocomplete(profile=profile_aucto)
    async def user_add(self, interaction: discord.Interaction, profile: str, user: discord.Member, reason: str, duration: app_commands.Transform[int, TimeConverter]):
        config = await self.backend.get_config(interaction.guild_id)
        if profile not in config.profiles.keys():
            return await interaction.response.send_message(f"Profile `{profile}` not found", ephemeral=True)
        profile_data = Profile(**config.profiles[profile])

        author_role = [role.id for role in interaction.user.roles]

        if not (set(author_role) & set(config.mod_roles)): 
            return await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)

        user_data = await self.backend.get_blacklist(user, profile_data)
        if user_data is not None: 
            return await interaction.response.send_message(f"{user.mention} is already blacklisted in profile `{profile}`", ephemeral=True)
        user_data = Blacklist(user_id=user.id, guild_id=interaction.guild_id, profile=profile_data._id, Blacklist_at=datetime.datetime.utcnow(), Blacklist_by=interaction.user.id, Blacklist_reason=reason, Blacklist_duration=duration, Blacklist_end=datetime.datetime.utcnow() + datetime.timedelta(seconds=duration))
        await self.backend.insert_blacklist(user_data)

        role_add = [interaction.guild.get_role(role_id) for role_id in profile_data.role_add]
        role_remove = [interaction.guild.get_role(role_id) for role_id in profile_data.role_remove]
        await user.add_roles(*role_add, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")
        await user.remove_roles(*role_remove, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(f"{user.mention} has been blacklisted in profile `{profile}`", ephemeral=True)

        if config.log_channel:
            channel: discord.TextChannel = interaction.guild.get_channel(config.log_channel)
            embed = discord.Embed(title="Blacklist", description=f"", color=discord.Color.red())
            embed.description += f"**User:** {user.mention} ({user.id})\n"
            embed.description += f"**Profile:** {profile}\n"
            embed.description += f"**Reason:** {reason}\n"
            embed.description += f"**Duration:** {format_timespan(duration)}\n"
            embed.description += f"**End:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\n"
            embed.description += f"**By:** {interaction.user.mention} ({interaction.user.id})\n"
            await channel.send(embed=embed)
    
    @user.command(name="remove", description="remove blacklist from user")
    @app_commands.describe(profile="Profile to remove blacklist", user="User to remove blacklist", reason="Reason for removing blacklist")
    @app_commands.autocomplete(profile=profile_aucto)
    async def user_remove(self, interaction: discord.Interaction, profile: str, user: discord.Member, reason: str=None):
        config = await self.backend.get_config(interaction.guild_id)
        if profile not in config.profiles.keys():
            return await interaction.response.send_message(f"Profile `{profile}` not found", ephemeral=True)
        profile_data = Profile(**config.profiles[profile])

        author_role = [role.id for role in interaction.user.roles]
        if not (set(author_role) & set(config.mod_roles)): 
            return await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)

        user_data = await self.backend.get_blacklist(user, profile_data)
        if user_data is None:
            return await interaction.response.send_message(f"{user.mention} is not blacklisted in profile `{profile}`", ephemeral=True)
        
        role_add = [interaction.guild.get_role(role_id) for role_id in profile_data.role_remove]
        role_remove = [interaction.guild.get_role(role_id) for role_id in profile_data.role_add]
        await user.add_roles(*role_add, reason=f"Blacklist removed by {interaction.user} ({interaction.user.id})")
        await user.remove_roles(*role_remove, reason=f"Blacklist removed by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(f"{user.mention} has been removed from blacklist in profile `{profile}`", ephemeral=True)
        await self.backend.blacklist.delete({"user_id": user.id, "profile": profile_data._id, "guild_id": interaction.guild_id})

    @user.command(name="view", description="View blacklist of user")
    @app_commands.describe(user="User to view blacklist")
    async def _view(self, interaction: discord.Interaction, user: discord.Member):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return await interaction.response.send_message("This server doesn't have blacklist", ephemeral=True)
        pages = []
        for blacklist in await self.backend.blacklist.find_many_by_custom({"user_id": user.id, "guild_id": interaction.guild_id}):
            profile = Profile(**config.profiles[blacklist["profile"]])
            embed = discord.Embed(title=f"Blacklist of {user}", color=self.bot.default_color, description="")
            embed.description += f"**Profile:** {profile._id}\n"
            embed.description += f"**Reason:** {blacklist['Blacklist_reason']}\n"
            embed.description += f"**Duration:** {format_timespan(blacklist['Blacklist_duration'])}\n"
            embed.description += f"**End:** <t:{int(blacklist['Blacklist_end'].timestamp())}:R>\n"
            embed.description += f"**By:** <@{blacklist['Blacklist_by']}> ({blacklist['Blacklist_by']})\n"
            pages.append(embed)
        if len(pages) == 0:
            return await interaction.response.send_message(f"{user.mention} is not blacklisted", ephemeral=True)
        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0], ephemeral=False)
        else:
            await Paginator(interaction, pages=pages).start(embeded=True,quick_navigation=False, hidden=False)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.backend.get_config(member.guild.id)
        if config is None:
            return
        for blacklist in await self.backend.blacklist.find_many_by_custom({"user_id": member.id, "guild_id": member.guild.id}):
            profile = Profile(**config.profiles[blacklist["profile"]])
            role_add = [member.guild.get_role(role_id) for role_id in profile.role_add]
            role_remove = [member.guild.get_role(role_id) for role_id in profile.role_remove]

            await member.add_roles(*role_add, reason=f"Presistent blacklist by {member.guild.me} ({member.guild.me.id})")
            await member.remove_roles(*role_remove, reason=f"Presistent blacklist by {member.guild.me} ({member.guild.me.id})")
            blacklist["Blacklist_end"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=blacklist["Blacklist_duration"])
            blacklist["Blacklist_at"] = datetime.datetime.utcnow()
            await self.backend.blacklist.update(blacklist)

async def setup(bot):
    await bot.add_cog(Blacklist_cog(bot))