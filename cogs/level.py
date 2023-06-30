import discord
import math
import datetime
from discord import app_commands
from discord import Interaction
from discord.ext import commands
from utils.db import Document
from PIL import Image, ImageDraw, ImageFont, ImageChops
from io import BytesIO



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
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in await self.levels.config.get_all():
            self.levels.config_cache[guild['_id']] = guild

        for member in await self.levels.ranks.get_all():
            self.levels.level_cache[member['_id']] = member

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
    async def on_slash_command(self, message: discord.Message):
        config = await self.levels.get_config(message.guild)
        if not config['enabled']: return

        if not message.interaction: return
        user = message.interaction.user
        data = await self.levels.get_member_level(user)
        if data['last_updated'] is None or data['last_updated'] + datetime.timedelta(seconds=8) < datetime.datetime.utcnow():
            pass
        else:
            return

        user_roles = [role.id for role in user.roles]
        if (set(user_roles) & set(config['blacklist']['roles'])):
            return
        if str(message.channel.id) in config['blacklist']['channels']:
            return
        
        expirience = 1 * config['global_multiplier']
        if str(message.channel.id) in config['multipliers']['channels'].keys():
            expirience = expirience * config['multipliers']['channels'][str(message.channel.id)]
        
        for role in user_roles:
            if str(role) in config['multipliers']['roles'].keys():
                expirience = expirience * config['multipliers']['roles'][str(role)]

        data['xp'] += expirience
        data['weekly'] += 1
        data['last_updated'] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data['xp'])
        if level > data['level']:
            data['level'] = level
            if str(level) in config['rewards'].keys():
                for role in config['rewards'][str(level)]:
                    role = message.guild.get_role(role)
                    if role is None: continue
                    await user.add_roles(role)
        
        print(f"user {user} got {expirience} by slash command")


    @commands.Cog.listener()
    async def on_level_up(self, message: discord.Message, data: dict):
        config = await self.levels.get_config(message.guild)
        expirience = 1
        if not config['enabled']:
            return
        user_roles = [role.id for role in message.author.roles]
        if (set(user_roles) & set(config['blacklist']['roles'])):
            return
        if str(message.channel.id) in config['blacklist']['channels']:
            return

        expirience = expirience * config['global_multiplier']
        if str(message.channel.id) in config['multipliers']['channels'].keys():
            expirience = expirience * config['multipliers']['channels'][str(message.channel.id)]

        for role in user_roles:
            if str(role) in config['multipliers']['roles'].keys():
                expirience = expirience * config['multipliers']['roles'][str(role)]
        
        data['xp'] += expirience
        data['weekly'] += 1
        data['last_updated'] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data['xp'])
        if level > data['level']:
            data['level'] = level
            if str(level) in config['rewards'].keys():
                role = message.guild.get_role(config['rewards'][str(level)])
                if role is None: return
                await message.author.add_roles(role)
            #     await message.channel.send(f"Congratulations {message.author.mention} you have leveled up to level {level} and have been given the {role.n} role!")
            # await message.channel.send(f"Congratulations {message.author.mention} you have leveled up to level {level}!")
    
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

async def setup(bot):
    await bot.add_cog(Level(bot))