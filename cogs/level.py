import asyncio
import aiohttp
from io import BytesIO
from typing import List, Literal
import discord
import math
import datetime
import random
import pytz
import pandas as pd
from discord import app_commands
from discord import Interaction
from discord.ext import commands, tasks
from utils.db import Document
from utils.transformer import TimeConverter, MutipleRole, DMCConverter
from utils.views.giveaway import Giveaway
from utils.converters import DMCConverter_Ctx
from utils.views.modal import General_Modal
from utils.paginator import Paginator
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops



class Level_DB:
    def __init__(self, bot):
        self.bot = bot
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
        experience = 20 * (level - 1) ** 2 + 35
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
            "weekly":{
                "required_messages": None,
                "role": None,
            }
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

    async def millify(self, n):
        n = float(n)
        millnames = ['',' K',' M',' Bil']
        millidx = max(0,min(len(millnames)-1,
                            int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    # return '{:.1f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
        return f'{round(n / 10**(3 * millidx),1):0}{millnames[millidx]}'


    async def round_pfp(self, pfp: discord.Member | discord.Guild):
        if isinstance(pfp, discord.Member):
            if pfp.avatar is None:
                pfp = pfp.default_avatar.with_format("png")
            else:
                pfp = pfp.avatar.with_format("png")
        else:
            pfp = pfp.icon.with_format("png")

        pfp = BytesIO(await pfp.read())
        pfp = Image.open(pfp)
        pfp = pfp.resize((124, 124), Image.Resampling.LANCZOS).convert('RGBA')
        
        bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new('L', bigzise, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigzise, fill=255)
        mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)

        return pfp

    async def create_rank_card(self, member: discord.Member, rank: str, level: str,exp: str, weekly: str):
        base_image = Image.open('./assets/rank_card.png')
        profile = member.avatar.with_format('png')
        profile = await self.round_pfp(member)
        profile = profile.resize((124, 124), Image.Resampling.LANCZOS).convert('RGBA')

        user: discord.User = await self.bot.fetch_user(member.id)
        if user.banner is None:
            banner = Image.new('RGBA', (372, 131), user.accent_color.to_rgb())
            base_image.paste(banner, (0, 0), banner)
        else:
            banner = user.banner.with_format("png")
            banner = BytesIO(await banner.read())
            banner = Image.open(banner)
            banner = banner.resize((372, 131), Image.Resampling.LANCZOS).convert('RGBA')
            base_image.paste(banner, (0, 0), banner)            
        
        pfp_backdrop = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
        back_draw = ImageDraw.Draw(pfp_backdrop)
        back_draw.ellipse((3, 3, 137, 137), fill=(33, 33, 33, 255))
        base_image.paste(pfp_backdrop, (16, 33), pfp_backdrop)

        base_image.paste(profile, (25, 41), profile)

        draw = ImageDraw.Draw(base_image)
        draw.text((129, 175),
                  member.display_name,
                  fill="#FFFFFF", font=ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 30))        

        draw.text((28, 277), f"{str(rank)}", fill="#6659CE", font=ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 35))        
        draw.text((206, 277), f"{str(level)}", fill="#6659CE", font=ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 35))
        draw.text((28, 389), f"{str(exp)}", fill="#6659CE", font=ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 35))
        draw.text((206, 389), f"{str(weekly)}", fill="#6659CE", font=ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 35))
        return base_image

class Level(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = Level_DB(bot)
        self.bot.level = self.levels
        self.webhook = None
    
    weekly = app_commands.Group(name="weekly", description="Weekly commands")

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
    async def on_member_remove(self, member: discord.Member):
        if member.bot: return
        if member.guild.id != 785839283847954433: return
        guild: discord.Guild = member.guild
        try:
            ban = await guild.fetch_ban(member)        
            if ban: return
        except discord.NotFound:
            pass
        member_data = await self.levels.get_member_level(member)
        if member_data['weekly'] < 10:
            if member_data['level'] > 5: return
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
            embed.description += f"**Unban in** <t:{round(data['unbanAt'].timestamp())}:R>\n"
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
        if data['weekly'] >= config['weekly']['required_messages']:
            role = message.guild.get_role(config['weekly']['role'])
            if role is None: return
            if role in user.roles: return
            await user.add_roles(role, reason="Reached required messages for weekly role")

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
        if data['weekly'] >= 100:
            role = message.guild.get_role(1128307039672737874)
            if role is None: return
            if role in message.author.roles: return
            await message.author.add_roles(role, reason="100 messages in a week")

    @app_commands.command(name="rank", description="View your rank card")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    async def rank(self, interaction: Interaction, member: discord.Member = None):
        await interaction.response.defer()
        member = member if member else interaction.user
        ranks = await self.levels.ranks.get_all()
        df = pd.DataFrame(ranks)
        df = df.sort_values(by=['xp'], ascending=False)
        df = df.reset_index(drop=True)
        rank: str = df[df['_id'] == member.id].index[0]
        level: str = df[df['_id'] == member.id]['level'].values[0]
        exp: str = await self.levels.millify(df[df['_id'] == member.id]['xp'].values[0])
        weekly: str = await self.levels.millify(df[df['_id'] == member.id]['weekly'].values[0])
        card = await self.levels.create_rank_card(member, rank, level, exp, weekly)

        with BytesIO() as image_binary:
            card.save(image_binary, 'PNG')
            image_binary.seek(0)
            embed = discord.Embed()
            embed.color = self.bot.default_color
            embed.set_image(url="attachment://rank.png")
            await interaction.followup.send(file=discord.File(fp=image_binary, filename='rank.png'), embed=embed)

    @rank.error
    async def rank_error(self, interaction: Interaction, error):
        raise error

    @app_commands.command(name="leaderboard", description="View the server's leaderboard")
    @app_commands.checks.cooldown(1, 10, key=lambda i:(i.guild_id, i.user.id))
    @app_commands.choices(type=[app_commands.Choice(name="Exp", value="xp"), app_commands.Choice(name="Weekly", value="weekly"), app_commands.Choice(name="Level", value="level")])
    async def leaderboard(self, interaction: Interaction, type: str):
        await interaction.response.defer()
        ranks = await self.levels.ranks.get_all()
        df = pd.DataFrame(ranks)
        df = df.sort_values(by=[f'{type}'], ascending=False)
        df = df.reset_index(drop=True)
        
        user_rank = df[df['_id'] == interaction.user.id].index[0] + 1

        embeds = []
        for i in range(0, len(df), 11):
            embed = discord.Embed(title=f"{interaction.guild.name}'s Leaderboard", description="", color=self.bot.default_color)
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            for index, row in df[i:i+11].iterrows():
                member = interaction.guild.get_member(row['_id'])
                if member is None: continue
                if row['xp'] < 35:
                    exp = 0
                else:
                    exp = await self.levels.millify(row['xp'])
                if member.id == interaction.user.id:
                    embed.description += f"**{index}.** **{member.mention}** <:pin:1000719163851018340> \n"
                else:
                    embed.description += f"**{index}.** {member.mention}\n"
                embed.description += f"<:invis_space:1067363810077319270> **Level:** {row['level']} | **Exp:** {exp} | **Weekly:** {row['weekly']}\n\n"
                embed.set_footer(text=f"Your Rank: {user_rank}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
            embeds.append(embed)
        await Paginator(interaction, embeds).start(embeded=True, timeout=60, hidden=False, quick_navigation=False, deffered=True)


    @app_commands.command(name="set", description="Set a user's level")
    @app_commands.checks.has_permissions(administrator=True)
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
        await self.levels.update_member_level(member, data)
    
    @app_commands.command(name="reset", description="Reset a user's level")
    @app_commands.checks.has_permissions(administrator=True)
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
        await self.levels.update_member_level(member, {"xp": 0, "level": 0, "weekly": 0, "last_updated": datetime.datetime.utcnow()})

    @weekly.command(name="reset", description="Reset a server's weekly xp")
    @app_commands.checks.has_permissions(administrator=True)
    async def weekly_reset(self, interaction: Interaction):
        await interaction.response.send_message(embed=discord.Embed(description="Please wait... This may take a while"), ephemeral=True)
        data = await self.levels.ranks.get_all()
        new_data = []
        for i in data:
            i['weekly'] = 0
            new_data.append(i)
            self.levels.level_cache[i['_id']] = i
        await self.levels.ranks.bulk_update(new_data)
        config = await self.levels.get_config(interaction.guild)
        if config['weekly']['required_messages'] != 0:
            role = interaction.guild.get_role(1128307039672737874)
            if role is None: return
            for member in interaction.guild.members:
                if role in member.roles:
                    await member.remove_roles(role, reason="Weekly reset")
                    await asyncio.sleep(0.5)
        await interaction.edit_original_response(content="Succesfully reset weekly xp", embed=None)            

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
            "blacklist": [],
            "dm_message": "Please dm Host to claim your prize!",
            "global_bypass": []
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

    async def update_giveaway(self, message: discord.Message, data: dict):
        await self.giveaways.update(data)
        self.giveaways_cache[message.id] = data

class Giveaways(commands.GroupCog, name="giveaways"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Giveaways_Backend(bot)
        self.bot.giveaway = self.backend
        self.giveaway_task = self.giveaway_loop.start()
        self.giveaway_task_progress = False
        self.giveaway_in_prosses = []
        self.context_end = app_commands.ContextMenu(name="End Giveaway", callback=self._giveaway_end)
        self.context_reroll = app_commands.ContextMenu(name="Reroll Giveaway", callback=self._giveaway_reroll)
        self.bot.tree.add_command(self.context_reroll)
        self.bot.tree.add_command(self.context_end)
    
    def cog_unload(self):
        self.giveaway_task.cancel() 
    
    async def now(self):
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)
        return now

    @tasks.loop(minutes=3)
    async def giveaway_loop(self):
        if self.giveaway_task_progress == True:
            return
        self.giveaway_task_progress = True
        now = datetime.datetime.utcnow()
        giveaways = self.backend.giveaways_cache.copy()
        for giveaway in giveaways.values():
            try:
                if giveaway["end_time"] <= now:
                    if giveaway["_id"] in self.giveaway_in_prosses:
                        continue
                    if giveaway["ended"] == True:
                        continue
                    self.bot.dispatch("giveaway_end", giveaway)
                    self.giveaway_in_prosses.append(giveaway["_id"])
                    del self.backend.giveaways_cache[giveaway["_id"]]
            except:
                pass
        self.giveaway_task_progress = False

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_giveaway_end(self, giveaway: dict):
        guild: discord.Guild = self.bot.get_guild(giveaway['guild'])
        channel: discord.TextChannel = guild.get_channel(giveaway['channel'])
        host: discord.Member = guild.get_member(giveaway['host'])
        if giveaway['ended'] == True: return
        try:
            message: discord.Message = await channel.fetch_message(giveaway['_id'])
        except discord.NotFound:
            try:
                await self.backend.giveaways.delete(giveaway['_id'])
                del self.backend.giveaways_cache[giveaway['_id']]
                self.giveaway_in_prosses.remove(giveaway['_id'])
            except:pass
        
        if len(giveaway['entries'].keys()) == 0 or len(giveaway['entries']) < giveaway['winners']:
            view = Giveaway()
            view.children[0].disabled = True
            await message.edit(view=view, content="**Giveaway Ended**")
            await message.reply(embed=discord.Embed(description="No one entered the giveaway or there were not enough entries to pick a winner", color=self.bot.default_color))
            await self.backend.giveaways.delete(giveaway['_id'])
            try:
                self.giveaway_in_prosses.remove(giveaway['_id'])
            except:
                pass
            try:
                del self.backend.giveaways_cache[giveaway['_id']]
            except:
                pass
            log_data = {
            "guild": guild,
            "channel": channel,
            "message": message,
            "prize": giveaway['prize'],
            "winners": [],
            "winner": [],
            "host": host,
            "item": giveaway['item'] if giveaway['dank'] else None,
            "participants": len(giveaway['entries'].keys()),
            }
            self.bot.dispatch("giveaway_end_log", log_data)
            return
        
        entries: List[int] = []
        for key, value in giveaway['entries'].items():
            if int(key) in entries: continue
            entries.extend([int(key)]*value)
        
        winners: List[discord.Member] = []
        while len(winners) != giveaway['winners']:
            winner = random.choice(entries)
            member = guild.get_member(winner)
            if member is None: continue
            if member in winners: continue
            winners.append(member)
            if len(winners) == giveaway['winners']: break
        
        embed: discord.Embed = message.embeds[0]
        if len(embed.fields) != 0:
            fields_name = [field.name for field in embed.fields]
            if "Winners" in fields_name:
                embed.set_field_at(fields_name.index("Winners"), name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)
            else:
                embed.description += f"\n**Total Participants:** {len(giveaway['entries'].keys())}"
                embed.add_field(name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)
        else:
            embed.description += f"\n**Total Participants:** {len(giveaway['entries'].keys())}"
            embed.add_field(name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)

        view = Giveaway()
        view.children[0].disabled = True
        await message.edit(view=view, content="**Giveaway Ended**", embed=embed)

        win_embed = discord.Embed(title="Congratulations", color=self.bot.default_color, description="")
        dm_embed = discord.Embed(title="You won a giveaway!", description=f"**Congratulations!** you won", color=self.bot.default_color)
        host_embed = discord.Embed(title=f"Your Giveaway ", description="", color=self.bot.default_color)
        if giveaway['dank']:
            if giveaway['item']:
                item = await self.bot.dank_items.find(giveaway['item'])
                win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** {giveaway['prize']}x {giveaway['item']}\n"
                dm_embed.description += f" {giveaway['prize']}x {giveaway['item']} in {guild.name}"
                host_embed.title += f"{giveaway['prize']}x {giveaway['item']} has ended"
            else:
                item = None
                win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** ⏣ {giveaway['prize']:,}\n"
                dm_embed.description += f" ⏣ {giveaway['prize']:,} in {guild.name}"
                host_embed.title += f"⏣ {giveaway['prize']:,} has ended"
        else:
            win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** {giveaway['prize']}\n"
            dm_embed.description += f" {giveaway['prize']} in {guild.name}"
            host_embed.title += f"{giveaway['prize']} has ended"

        win_message = await message.reply(embed=win_embed, content=",".join([winner.mention for winner in winners]))
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Jump", url=message.jump_url, style=discord.ButtonStyle.link))

        for winner in winners:
            try:
                await winner.send(embed=dm_embed, view=link_view)
            except:
                pass
            if giveaway['dank']:
                try:await self.bot.create_payout(event="Giveaway", winner=winner, host=host, prize=giveaway['prize'], message=win_message, item=item)
                except:pass
        
        host_embed.description += f"**Ended at:** <t:{int(datetime.datetime.now().timestamp())}:R>\n"
        host_embed.description += f"**Total Entries:** {len(giveaway['entries'].keys())}\n"
        host_embed.description += f"**Winners:** \n"
        for winner in winners: host_embed.description += f"> {winners.index(winner)+1}. {winner.mention}\n"
        try:
            await host.send(embed=host_embed, view=link_view)
        except:
            pass

        giveaway['ended'] = True
        await self.backend.update_giveaway(message, giveaway)
        try:
            self.giveaway_in_prosses.remove(giveaway['_id']); 
        except ValueError:
            pass
        log_data = {
            "guild": guild,
            "channel": channel,
            "message": message,
            "prize": giveaway['prize'],
            "winners": winners,
            "winner": giveaway['winners'],
            "host": host,
            "item": giveaway['item'] if giveaway['dank'] else None,
            "participants": len(giveaway['entries'].keys()),

        }
        self.bot.dispatch("giveaway_end_log", log_data)
                
    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys()
            ]
        else:
            return choices[:24]

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Giveaway())
        for guild in await self.backend.config.get_all():
            self.backend.config_cache[guild["_id"]] = guild
        
        for giveaway in await self.backend.giveaways.get_all():
            if giveaway["ended"] == True: continue
            self.backend.giveaways_cache[giveaway["_id"]] = giveaway
    
    @app_commands.command(name="start", description="Start a giveaway")
    @app_commands.describe(
        winners="Number of winners", prize="Prize of the giveaway", item="Item to giveaway", duration="Duration of the giveaway",
        req_roles="Roles required to enter the giveaway", bypass_role="Roles that can bypass the giveaway", req_level="Level required to enter the giveaway",
        req_weekly="Weekly XP required to enter the giveaway", donor="Donor of the giveaway", message="Message to accompany the giveaway", dank="Dank Memer Giveaway?"
    )
    @app_commands.autocomplete(item=item_autocomplete)
    async def _start(self, interaction: discord.Interaction, winners: app_commands.Range[int, 1, 20], prize: str,
                     duration: app_commands.Transform[int, TimeConverter],
                     dank: bool=True,
                     item:str=None,
                     req_roles: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     bypass_role: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     req_level: app_commands.Range[int, 1, 100]=None,
                     req_weekly: app_commands.Range[int, 1, 100]=None,
                     donor: discord.Member=None,
                     message: app_commands.Range[str, 1, 250]=None,
    ):
        await interaction.response.defer()
        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.followup.send("Giveaways are not enabled in this server!", ephemeral=True)
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.followup.send("You do not have permission to start giveaways!", ephemeral=True)
        if dank == True:
            prize = await DMCConverter_Ctx().convert(interaction, prize)
            if not isinstance(prize, int):
                return await interaction.followup.send("Invalid prize!", delete_after=5)
        data = {
            "_id": None,
            "channel": interaction.channel.id,
            "guild": interaction.guild.id,
            "winners": winners,
            "prize": prize,
            "item": item if item else None,
            "duration": duration,
            "req_roles": [role.id for role in req_roles] if req_roles else [],
            "bypass_role": [role.id for role in bypass_role] if bypass_role else [],
            "req_level": req_level,
            "req_weekly": req_weekly,
            "entries": {},
            "start_time": datetime.datetime.utcnow(),
            "end_time": (datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)),
            "ended": False,
            "host": interaction.user.id,
            "donor": donor.id if donor else None,
            "message": message if message else None,
            "dank": dank
        }
        embed = discord.Embed(color=interaction.client.default_color, description="")

        if dank:
            if item:
                embed.description += f"## {prize}x {item}\n"
            else:
                try:
                    embed.description += f"## ⏣ {prize:,}\n"
                except:
                    embed.description += f"## ⏣ {prize}\n"
        else:
            embed.description += f"## Prize: {prize}\n"
        embed.description += "‎\n"
        timnestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())
        embed.description += f"**End Time:** <t:{timnestamp}:R> (<t:{timnestamp}:T>)\n"
        embed.description += f"**Winners:** {winners}\n"
        embed.description += f"**Host:** {interaction.user.mention}\n"
        if donor:
            embed.description += f"**Donor:** {donor.mention}"
        if req_roles:
            value = ""
            if len(req_roles) == 2:
                value = f"{req_roles[0].mention} and {req_roles[1].mention}"
            else:
                value = ", ".join([role.mention for role in req_roles])
            embed.add_field(name="Required Roles", value=value, inline=True)
        if bypass_role:
            value = ""
            if len(bypass_role) == 2:
                value = f"{bypass_role[0].mention} and {bypass_role[1].mention}"
            else:
                value = ", ".join([role.mention for role in bypass_role])
            embed.add_field(name="Bypass Roles", value=value, inline=False)
        if req_level:
            embed.add_field(name="Required Level", value=str(req_level), inline=True)
        if req_weekly:
            embed.add_field(name="Required Weekly XP", value=str(req_weekly), inline=False)
        embed.timestamp = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        embed.set_footer(text=f"{winners} winner{'s' if winners > 1 else ''} | Ends at")
        await interaction.followup.send(embed=embed, view=Giveaway(), content="<a:tgk_tadaa:806631994770849843> **GIVEAWAY STARTED** <a:tgk_tadaa:806631994770849843>")
        if message:
            host_webhook = None
            for webhook in await interaction.channel.webhooks():
                if webhook.user.id == self.bot.user.id:
                    host_webhook = webhook
                    break
            if not host_webhook:
                pfp = await self.bot.user.avatar.read()
                host_webhook = await interaction.channel.create_webhook(name="Giveaway Host", avatar=pfp)
            
            author = donor if donor else interaction.user
            await host_webhook.send(content=message, username=author.global_name, avatar_url=author.avatar.url if author.avatar else author.default_avatar, allowed_mentions=discord.AllowedMentions.none())

        msg = await interaction.original_response()
        data['_id'] = msg.id
        await self.backend.giveaways.insert(data)
        self.backend.giveaways_cache[msg.id] = data
        self.bot.dispatch("giveaway_host", data)
    
    @app_commands.command(name="reroll", description="Reroll a giveaway")
    @app_commands.describe(
        message="Message to accompany the reroll",
        winners="Numbers of winners to reroll"
    )
    @app_commands.rename(message="message_id")
    async def _reroll(self, interaction: discord.Interaction, message: str, winners: app_commands.Range[int, 1, 10]=1):
        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.followup.send("Giveaways are not enabled in this server!", ephemeral=True)
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.response.send_message("You do not have permission to start giveaways!", ephemeral=True)

        try:
            message = await interaction.channel.fetch_message(int(message))
        except:
            return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
        
        giveawa_data = await self.backend.get_giveaway(message)
        if not giveawa_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        if not giveawa_data['ended']: return await interaction.response.send_message("This giveaway has not ended!", ephemeral=True)
        giveawa_data['winners'] = winners
        self.bot.dispatch("giveaway_end", giveawa_data)
        await interaction.response.send_message("Giveaway rerolled successfully! Make sure to cancel the already queued payouts use `/payout search`", ephemeral=True)
        chl = interaction.client.get_channel(1130057933468745849)
        await chl.send(f"Rerolled giveaway by {interaction.user.mention} in {interaction.guild.name} for {winners} winners {message.jump_url}")

    
    

    @app_commands.command(name="end", description="End a giveaway")
    @app_commands.describe(
        message="Message to accompany the end"
    )
    @app_commands.rename(message="message_id")
    async def _end(self, interaction: discord.Interaction, message: str):
        try:
            message = await interaction.channel.fetch_message(int(message))
        except:
            return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
        giveaway_data = await self.backend.get_giveaway(message)
        if not giveaway_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
        self.bot.dispatch("giveaway_end", giveaway_data)
        await interaction.response.send_message("Giveaway ended successfully!", ephemeral=True)
        try:
            self.bot.giveaway.giveaways_cache.pop(message.id)
        except Exception as e:
            raise e

    @commands.command(name="multiplier", description="Set the giveaway multiplier", aliases=['multi'])
    async def _multiplier(self, ctx, user: discord.Member=None):
        user = user if user else ctx.author
        config = await self.backend.get_config(ctx.guild)
        if not config: return await ctx.send("This server is not set up!")
        if len(config['multipliers'].keys()) == 0: return await ctx.send("This server does not have any multipliers!")
        user_role = [role.id for role in user.roles]
        embed = discord.Embed(color=self.bot.default_color, description=f"@everyone - `1x`\n")
        embed.set_author(name=f"{user}'s Multipliers", icon_url=user.avatar.url if user.avatar else user.default_avatar)
        total = 1
        for role, multi in config['multipliers'].items():
            if int(role) in user_role:
                embed.description += f"<@&{role}> - `{multi}x`\n"
                total += multi
        embed.description += f"**Total Multiplier** - `{total}x`"
        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_giveaway_end_log(self, giveaway_data: dict):
        config = await self.backend.get_config(giveaway_data['guild'])
        if not config: return
        if not config['log_channel']: return
        chl = self.bot.get_channel(config['log_channel'])
        if not chl: return

        embed = discord.Embed(color=self.bot.default_color,description="", title="Giveaway Ended", timestamp=datetime.datetime.now())
        embed.add_field(name="Host", value=giveaway_data['host'].mention)
        embed.add_field(name="Channel", value=giveaway_data['channel'].mention)
        embed.add_field(name="Number of Winners", value=giveaway_data['winner'])
        embed.add_field(name="Winners", value="\n".join([winner.mention for winner in giveaway_data['winners']] if giveaway_data['winners'] else ["`None`"]))
        if giveaway_data['item']:
            embed.add_field(name="Item", value=giveaway_data['item'])
        if giveaway_data['prize']:
            embed.add_field(name="Prize", value=giveaway_data['prize'])
        embed.add_field(name="Participants", value=giveaway_data['participants'])
        embed.add_field(name="Message", value=f"[Click Here]({giveaway_data['message'].jump_url})")
        embed.add_field(name="Total Participants", value=giveaway_data['participants'])
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=giveaway_data['message'].jump_url))
        await chl.send(embed=embed, view=view)
    
    @commands.Cog.listener()
    async def on_giveaway_host(self, data: dict):
        config = await self.backend.get_config(self.bot.get_guild(data['guild']))
        if not config: return
        if not config['log_channel']: return
        chl = self.bot.get_channel(config['log_channel'])
        if not chl: return

        embed = discord.Embed(color=self.bot.default_color,description="", title="Giveaway Hosted", timestamp=datetime.datetime.now())
        embed.add_field(name="Host", value=f"<@{data['host']}>")
        embed.add_field(name="Channel", value=f"<#{data['channel']}>")
        
        embed.add_field(name="Winners", value=data['winners'])
        if data['dank'] == True:
            if data['item']:
                embed.add_field(name="Prize", value=f"{data['prize']}x {data['item']}")
            else:
                embed.add_field(name="Prize", value=f"{data['prize']:,}")
        else:
            embed.add_field(name="Prize", value=f"{data['prize']}")
        embed.add_field(name="Link", value=f"[Click Here](https://discord.com/channels/{data['guild']}/{data['channel']}/{data['_id']})")
        embed.add_field(name="Ends At", value=data['end_time'].strftime("%d/%m/%Y %H:%M:%S"))
        await chl.send(embed=embed)


    async def _giveaway_end(self, interaction: discord.Interaction, message: discord.Message):        
        if message.author.id != self.bot.user.id: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)

        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.response.send_message("Giveaways are not enabled in this server!", ephemeral=True)
        
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.response.send_message("You do not have permission to start giveaways!", ephemeral=True)
        
        giveaway_data = await self.backend.get_giveaway(message)
        if not giveaway_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
        self.bot.dispatch("giveaway_end", giveaway_data)
        await interaction.response.send_message("Giveaway ended successfully!", ephemeral=True)
        try:
            self.bot.giveaway.giveaways_cache.pop(message.id)
        except Exception as e:
            raise e

    async def _giveaway_reroll(self, interaction: discord.Interaction, message: discord.Message):
        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.response.send_message("Giveaways are not enabled in this server!", ephemeral=True)
        
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.response.send_message("You do not have permission to start giveaways!", ephemeral=True)

        if message.author.id != self.bot.user.id: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        giveaway_data = await self.backend.get_giveaway(message)
        titile = "Reroll Giveaway for"
        modal = General_Modal(title="Reroll Giveawy", interaction=interaction)
        modal.winner_num = discord.ui.TextInput(label="Number of Winners", placeholder=giveaway_data['winners'], required=True)
        modal.add_item(modal.winner_num)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            try:
                winners = int(modal.winner_num.value)
            except:
                return await modal.interaction.response.send_message("Invalid number of winners!", ephemeral=True)
            giveaway_data['winners'] = winners
            self.bot.dispatch("giveaway_end", giveaway_data)
            await modal.interaction.response.send_message("Giveaway rerolled successfully! Make sure to cancel the already queued payouts use `/payout search`", ephemeral=True)
            chl = interaction.client.get_channel(1130057933468745849)
            await chl.send(f"Rerolled giveaway by {interaction.user.mention} in {interaction.guild.name} for {winners} winners {message.jump_url}")
        else:
            return


async def setup(bot):
    await bot.add_cog(Level(bot))
    await bot.add_cog(Giveaways(bot))