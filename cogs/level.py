import discord
import math
import datetime
from discord import app_commands
from discord import Interaction
from discord.ext import commands
from utils.db import Document
from utils.transformer import TimeConverter, MutipleRole
# from utils.views.giveaway import Giveaway



class Level_DB:
    def __init__(self, bot):
        self.db = bot.mongo["Levels"]
        self.ranks = Document(self.db, "Ranks")
        self.config = Document(self.db, "RankConfig")
        self.config_cache = {}
        self.level_cache = {}
    
    async def get_config(self, guild: discord.Guild):
        if guild.id in self.config_cache.keys():
            return self.config_cache[guild.id]
        config = await self.config.find(guild.id)
        if config is None:
            config = await self.guild_config_template(guild)
        self.config_cache[guild.id] = config
        return config

    async def update_config(self, guild: discord.Guild, data: dict):
        await self.config.update(data)
        self.config_cache[guild.id] = data       

    async def count_level(self, expirience: int):
        if expirience < 35:
            return 0
        level:int = math.floor(math.sqrt((expirience - 35) / 20)) + 1
        return level

    async def count_xp(self, level: int):
        if level < 1:
            return 0
        experience: int = math.ceil(((104 - 1) ** 2) * 20 + 35)
        return experience
    
    async def level_template(self, member: discord.Member):
        data = {
            "_id": member.id,
            "xp": 1,
            "level": 0,
            "weekly": 0,
            "last_updated": None
        }
        await self.ranks.insert(data)
        return data
    
    async def guild_config_template(self, guild: discord.Guild):
        data = {
            "_id": guild.id,
            "enabled": False,
            "cooldown": 8,
            "announcement_channel": None,
            "clear_on_leave": True,
            "blacklist": {
                "channels": [],
                "roles": [],
            },
            "global_multiplier": 1,
            "multipliers": {
                "roles": {},
                "channels": {},
            },
            "rewards": {},
        }
        await self.config.insert(data)
        return data
    
    async def get_member_level(self, member: discord.Member):
        if member.id in self.level_cache.keys():
            return self.level_cache[member.id]
        data = await self.ranks.find(member.id)
        if data is None:
            data = await self.level_template(member)
        self.level_cache[member.id] = data
        return data

    async def update_member_level(self, member: discord.Member, data: dict):
        await self.ranks.update(member.id, data)
        self.level_cache[member.id] = data

class Level(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = Level_DB(bot)
        self.bot.level = self.levels
        self.webhook = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in await self.levels.config.get_all():
            self.levels.config_cache[guild['_id']] = guild

        for member in await self.levels.ranks.get_all():
            self.levels.level_cache[member['_id']] = member
        
        channel = self.bot.get_channel(999736058071744583)
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                self.webhook = webhook
                break
        if self.webhook is None:
            avatar = await self.bot.user.avatar.read()
            self.webhook = await channel.create_webhook(name="Banish Logs", avatar=avatar)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            if message.interaction:
                self.bot.dispatch("slash_command", message)
            return
        if message.guild is None:
            return
        
        data = await self.levels.get_member_level(message.author)

        if data['last_updated'] is None:
            self.bot.dispatch("level_up", message, data)
            return
        if data['last_updated'] + datetime.timedelta(seconds=8) < datetime.datetime.utcnow():
            self.bot.dispatch("level_up", message, data)
    
    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        member = payload.user
        guild = self.bot.get_guild(payload.guild_id)

        if member.bot: return
        if payload.guild_id is None: return
        member_data = await self.levels.get_member_level(member)
        if member_data['weekly'] < 10 or member_data['level'] < 5:
            data = await self.bot.free.find(member.id)
            if data is None:
                data = {
                    "_id": member.id,
                    "total_ff": 1,
                    "banned": False,
                    "ban_days": 7,
                    "unbanAt": None,
                }
                await self.bot.free.insert(data)
            if data['total_ff'] == 1:
                data['unbanAt'] = datetime.datetime.utcnow() + datetime.timedelta(days=data['ban_days'])
            else:
                days = data['ban_days'] * data['total_ff']
                data['unbanAt'] = datetime.datetime.utcnow() + datetime.timedelta(days=days)
            await guild.ban(member, reason=f"Freeloaded after Heist. Total Freeloads: {data['total_ff']}")
            embed = discord.Embed(title="Freeloader Banned", description=f"", color=discord.Color.red())
            embed.description += f"**User:** {member.mention} | `{member.id}`\n"
            embed.description += f"**Total Freeloads:** {data['total_ff']}\n"
            embed.description += f"**Ban Duration:** {data['ban_days']} days\n"
            embed.description += f"**Uban In:** <t:{round(data['unbanAt'].timestamp())}:R>\n"
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar)
            embed.set_footer(text="The Gambler's Kingdom", icon_url=guild.icon.url)
            await self.webhook.send(embed=embed)
            data['total_ff'] += 1
            data['banned'] = True
            await self.bot.free.update(data)

    @commands.Cog.listener()
    async def on_slash_command(self, message: discord.Message):
        if message.guild is None: return
        config = await self.levels.get_config(message.guild)
        if config['enabled'] == False: return

        if not message.interaction: return
        user = message.interaction.user
        data = await self.levels.get_member_level(user)
        if data['last_updated'] is None or data['last_updated'] + datetime.timedelta(seconds=8) < datetime.datetime.utcnow():
            pass
        else:
            return
        mutiplier = 1

        mutiplier += config['global_multiplier']
        user_roles = [role.id for role in user.roles]
        if (set(user_roles) & set(config['blacklist']['roles'])):
            return
        if str(message.channel.id) in config['blacklist']['channels']:
            return

        if str(message.channel.id) in config['multipliers']['channels'].keys():
            mutiplier += config['multipliers']['channels'][str(message.channel.id)]
        
        for role in user_roles:
            if str(role) in config['multipliers']['roles'].keys():
                mutiplier += config['multipliers']['roles'][str(role)]

        expirience = 1
        expirience *= mutiplier
        data['xp'] += expirience
        data['weekly'] += 1
        data['last_updated'] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data['xp'])
        if level > data['level']:
            data['level'] = level
            roles = []
            for key, value in config['rewards'].items():
                if level >= int(key):
                    role = message.guild.get_role(value)
                    if role is None: continue
                    roles.append(role)
            if len(roles) > 0:
                await user.add_roles(*roles)

            level_up_embed = discord.Embed(description="", color=self.bot.default_color)
            level_up_embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar)
            level_up_embed.description += f"## Congratulations {user.mention}!\n you have leveled up to level {level}!"
            level_up_embed.set_footer(text="The Gambler's Kingdom", icon_url=message.guild.icon.url if message.guild.icon else None)
            annouce = message.guild.get_channel(config['announcement_channel'])
            if annouce is None: return
            await annouce.send(embed=level_up_embed, content=user.mention)

    @commands.Cog.listener()
    async def on_level_up(self, message: discord.Message, data: dict):
        config = await self.levels.get_config(message.guild)
        if config['enabled'] == False:
            return
        user_roles = [role.id for role in message.author.roles]
        if (set(user_roles) & set(config['blacklist']['roles'])):
            return
        if str(message.channel.id) in config['blacklist']['channels']:
            return

        multiplier = config['global_multiplier']

        if str(message.channel.id) in config['multipliers']['channels'].keys():
            multiplier += config['multipliers']['channels'][str(message.channel.id)]

        for role in user_roles:
            if str(role) in config['multipliers']['roles'].keys():
                multiplier += config['multipliers']['roles'][str(role)]
        
        exprience = 1
        exprience *= multiplier

        data['xp'] += exprience
        data['weekly'] += 1
        data['last_updated'] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data['xp'])
        if level > data['level']:
            data['level'] = level
            roles = []
            for key, value in config['rewards'].items():
                if level >= int(key):
                    role = message.guild.get_role(value)
                    if role is None: continue
                    roles.append(role)
            if len(roles) > 0:
                await message.author.add_roles(*roles)
            level_up_embed = discord.Embed(description="", color=self.bot.default_color)
            level_up_embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar)
            level_up_embed.description += f"## Congratulations {message.author.mention}!\n you have leveled up to level {level}!"
            level_up_embed.set_footer(text="The Gambler's Kingdom", icon_url=message.guild.icon.url if message.guild.icon else None)
            annouce = message.guild.get_channel(config['announcement_channel'])
            if annouce is None: return
            await annouce.send(embed=level_up_embed, content=message.author.mention)
    
        await self.levels.update_member_level(message.author, data)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rank_config(self, ctx):
        await self.levels.get_config(ctx.guild)
        await ctx.send("Rank config has been created!")

    @app_commands.command(name="rank", description="View your rank card")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    async def rank(self, interaction: Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user
        data = await self.levels.get_member_level(member)
        try:
            all_ranks = sorted(self.levels.level_cache.values(), key=lambda x: x['xp'], reverse=True)
            rank = all_ranks.index(data) + 1
            all_ranks = sorted(self.levels.level_cache.values(), key=lambda x: x['weekly'], reverse=True)
            weekly_rank = all_ranks.index(data) + 1
        except:
            pass

        embed = discord.Embed(color=interaction.client.default_color, description="")
        embed.set_author(name=member.name, icon_url=member.avatar.url if member.avatar else member.default_avatar)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar)
        embed.description += f"**Level:** {data['level']}\n"
        embed.description += f"**XP:** {data['xp']}\n"
        embed.description += f"**Weekly XP:** {data['weekly']}\n"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set", description="Set a user's level")
    @commands.has_permissions(administrator=True)
    async def set(self, interaction: Interaction, member: discord.Member, level: int):
        data = await self.levels.get_member_level(member)
        data['xp'] = await self.levels.count_xp(level)
        data['level'] = level
        await self.levels.update_member_level(member, data)
        await interaction.response.send_message(f"Succesfully set {member.mention}'s level to {level}")
        config = await self.levels.get_config(member.guild)
        roles = []
        for key, value in config['rewards'].items():
            if level >= int(key):
                role = member.guild.get_role(value)
                if role is None: continue
                roles.append(role)
        if len(roles) > 0:
            await member.add_roles(*roles)
    
    @app_commands.command(name="reset", description="Reset a user's level")
    @commands.has_permissions(administrator=True)
    async def reset(self, interaction: Interaction, member: discord.Member):
        data = await self.levels.get_member_level(member)
        await self.levels.ranks.delete(member.id)
        del self.levels.level_cache[member.id]
        await interaction.response.send_message(f"Reset {member.mention}'s level")
        config = await self.levels.get_config(member.guild)
        roles = []
        for key, value in config['rewards'].items():
            role = member.guild.get_role(value)
            if role is None: continue
            roles.append(role)
        await member.remove_roles(*roles)

class Giveaways_Backend:
    def __init__(self, bot):
        self.db = bot.mongo["Giveaways"]
        self.config = Document(self.db, "config")
        self.giveaways = Document(self.db, "giveaways")
        self.config_cache = {}
        self.giveaways_cache = {}

    async def get_config(self, guild: discord.Guild):
        if guild.id in self.config_cache.keys():
            return self.config_cache[guild.id]
        config = await self.config.find(guild.id)
        if config is None:
            config = await self.create_config(guild)
            self.config_cache[guild.id] = config
        return config
    
    async def create_config(self, guild: discord.Guild):
        data = {
            "_id": guild.id,
            "manager_roles": [],
            "log_channel": None,
            "multipliers": {},
            "blacklist": {},
        }
        await self.config.insert(data)
        return data
    
    async def update_config(self, guild: discord.Guild, data: dict):
        await self.config.update(data)
        self.config_cache[guild.id] = data
    
    async def get_giveaway(self, message: discord.Message):
        if message.id in self.giveaways_cache.keys():
            return self.giveaways_cache[message.id]
        giveaway = await self.giveaways.find(message.id)
        if giveaway is None: 
            return None
        return giveaway


class Giveaways(commands.GroupCog, name="giveaways"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Giveaways_Backend(bot)
        self.bot.giveaway = self.backend

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Giveaway())
        for guild in await self.backend.config.get_all():
            self.backend.config_cache[guild["_id"]] = guild
        
        for giveaway in await self.backend.giveaways.get_all():
            self.backend.giveaways_cache[giveaway["_id"]] = giveaway
    
    @app_commands.command(name="start", description="Start a giveaway")
    async def _start(self, interaction: discord.Interaction, winners: app_commands.Range[int, 1, 20], prize: str,
                     duraction: app_commands.Transform[int, TimeConverter], 
                     req_roles: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     bypass_role: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     req_level: app_commands.Range[int, 1, 100]=None,
                     req_weekly: app_commands.Range[int, 1, 100]=None,
    ):
        await interaction.response.defer()
        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.followup.send("Giveaways are not enabled in this server!", ephemeral=True)
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.followup.send("You do not have permission to start giveaways!", ephemeral=True)
        data = {
            "_id": None,
            "channel": interaction.channel.id,
            "guild": interaction.guild.id,
            "winners": winners,
            "prize": prize,
            "duration": duraction,
            "req_roles": [role.id for role in req_roles] if req_roles else [],
            "bypass_role": [role.id for role in bypass_role] if bypass_role else [],
            "req_level": req_level,
            "req_weekly": req_weekly,
            "entries": {},
            "start_time": datetime.datetime.now(),
            "end_time": datetime.datetime.now() + datetime.timedelta(seconds=duraction),
        }
        embed = discord.Embed(color=interaction.client.default_color, description="", title=prize)
        embed.description += f"**Winners:** {winners}\n"
        embed.description += f"**Duration:** <t:{round(data['end_time'].timestamp())}:R>\n"
        if req_roles:
            if len(req_roles) == 1:
                embed.description += f"**Required Role:** {req_roles[0].mention}\n"
            elif len(req_roles) == 2:
                embed.description += f"**Required Roles:** {req_roles[0].mention} and {req_roles[1].mention}\n"
            else:
                embed.description += f"**Required Roles:** {', '.join([role.mention for role in req_roles])}\n"
        if bypass_role:
            if len(bypass_role) == 1:
                embed.description += f"**Bypass Role:** {bypass_role[0].mention}\n"
            elif len(bypass_role) == 2:
                embed.description += f"**Bypass Roles:** {bypass_role[0].mention} and {bypass_role[1].mention}\n"
            else:
                embed.description += f"**Bypass Roles:** {', '.join([role.mention for role in bypass_role])}\n"
        if req_level:
            embed.description += f"**Required Level:** {req_level}\n"
        if req_weekly:
            embed.description += f"**Required Weekly:** {req_weekly}\n"
        if len(config['multipliers'].keys()) > 0:
            value = ""
            for role_id, multiplier in config['multipliers'].items():
                value += f"<@&{role_id}> - `{multiplier}`x\n"
            embed.add_field(name="Multipliers", value=value)
        
        await interaction.followup.send(embed=embed, view=Giveaway())
        msg = await interaction.original_response()
        data['_id'] = msg.id
        await self.backend.giveaways.insert(data)
        self.backend.giveaways_cache[msg.id] = data

async def setup(bot):
    await bot.add_cog(Level(bot))
    # await bot.add_cog(Giveaways(bot))