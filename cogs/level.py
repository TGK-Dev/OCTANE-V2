import discord
import datetime
import pandas as pd
import math
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from utils.db import Document
from utils.transformer import MutipleRole, MutipleChannel, MultipleMember
from PIL import Image, ImageDraw, ImageFont, ImageChops
from io import BytesIO
from typing import Union


class level(commands.GroupCog, name="level"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.level_config = Document(self.bot.db, "leveling")
        self.bot.level_config_cache = {}
    
    def template_db(self, guild_id:int) -> dict:
        return {
            "_id": guild_id,
            "blacklist": {
                "channels": [],
                "roles": [],
            },
            'multiplier': {'global': 1},
            'cooldown': 8,
            'clear_on_leave': True,
        }

    async def round_pfp(self, pfp: Union[discord.Member, discord.Guild]):
        if isinstance(pfp, discord.Member):
            if pfp.avatar is None:
                pfp = pfp.default_avatar.with_format('png')
            else:
                pfp = pfp.avatar.with_format('png')
        else:
                pfp = pfp.icon.with_format('png')

        pfp = BytesIO(await pfp.read())
        pfp = Image.open(pfp)
        pfp = pfp.resize((95, 95), Image.Resampling.LANCZOS).convert('RGBA')

        bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new('L', bigzise, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigzise, fill=255)
        mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)

        return pfp
    
    async def create_winner_card(self, guild: discord.Guild, data: list):
        template = Image.open('./assets/weekly_winner_template.png')
        guild_icon = await self.round_pfp(guild)
        template.paste(guild_icon, (15, 8), guild_icon)

        draw = ImageDraw.Draw(template)
        font = ImageFont.truetype('./assets/fonts/Clockwise-Light.ttf', 25)
        winner_name_font = ImageFont.truetype('./assets/fonts/Clockwise-Light.ttf', 28)
        winner_exp_font = ImageFont.truetype('./assets/fonts/Clockwise-Light.ttf', 20)
        
        winne_postions = {
            0: {'icon': (58, 150), 'name': (176, 165), 'xp': (176, 202)},
            1: {'icon': (58, 265), 'name': (176, 273), 'xp': (176, 309)},
            2: {'icon': (58, 380), 'name': (176, 392), 'xp': (176, 428)}}

        draw.text((116, 28), f"{guild.name}", font=font, fill="#DADBE3")
        for i in data[:3]:
            user = i['user']
            index = data.index(i)
            user_icon = await self.round_pfp(user)
            template.paste(user_icon, winne_postions[index]['icon'], user_icon)
            draw.text(winne_postions[index]['name'], f"{user.name}#{user.discriminator}", font=winner_name_font, fill="#9A9BD5")
            draw.text(winne_postions[index]['xp'], f"{i['xp']} XP", font=winner_exp_font, fill="#A8A8C8")

        return template
    
    manage = app_commands.Group(name="manage", description="Manage exp for a user")
    weekly = app_commands.Group(name="weekly", description="Weekly leaderboard")
    
    @manage.command(name="removeexp", description="remove a user's exp")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(users="The users to remove exp from", amount="The amount of exp to remove")
    async def remove(self, interaction: Interaction, users: app_commands.Transform[discord.Member, MultipleMember], amount: int):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we remove the exp", color=0x2b2d31))
        description = ""
        for user in users:
            data = await self.bot.ranks.find(user.id)
            if not data:
                Level_BackEnd.template_db(user.id)
                await self.bot.ranks.insert(data)
            data['xp'] -= amount
            await self.bot.ranks.update(data)
            self.bot.rank_cache[user.id] = data
            description += f"<:dynosuccess:1000349098240647188> | {user.mention} <:join:991733999477203054> - `{amount}` exp\n"
        
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x2b2d31))
    
    @manage.command(name="setexp", description="set a user's exp")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(users="The users to set exp to", amount="The amount of exp to set")
    async def set(self, interaction: Interaction, users: app_commands.Transform[discord.Member, MultipleMember], amount: int):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we set the exp", color=0x2b2d31))
        description = ""
        for user in users:
            data = await self.bot.ranks.find(user.id)
            if not data:
                Level_BackEnd.template_db(user.id)
                await self.bot.ranks.insert(data)
            data['xp'] = amount
            await self.bot.ranks.update(data)
            self.bot.rank_cache[user.id] = data
        
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x2b2d31))
    
    @weekly.command(name="winner", description="Get the weekly winner")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def weekly_reset(self, interaction: Interaction):
        await interaction.response.defer()
        data = await self.bot.ranks.get_all()
        data = sorted(data, key=lambda x: x['xp'], reverse=True)
        
        winners = []
        for i in range(3):
            winners.append({'user': interaction.guild.get_member(data[i]['_id']), 'xp': data[i]['xp']})

        image = await self.create_winner_card(interaction.guild, winners[:3])

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.followup.send(file=discord.File(fp=image_binary, filename=f'{interaction.guild.id}_weekly_winner_card.png'))
            image_binary.close()
        
        self.bot.dispatch("weekly_leaderboard_reset", interaction.channel)
class Level_BackEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.ranks = Document(self.bot.db, "ranks")
        self.bot.rank_cache = {}
        self.bot.rank_in_progress = {}
        self.bot.level_config_task = self.update_level_config.start()

    def cog_unload(self):
        self.bot.level_config_task.cancel()

    @staticmethod
    def template_db(user_id):
        return {
            "_id": user_id,
            "xp": 0,
            "last_updated": None,
        }
    
    async def millify(self, n):
        n = float(n)
        millnames = ['',' K',' M',' Bil']
        millidx = max(0,min(len(millnames)-1,
                            int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    # return '{:.1f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
        return f'{round(n / 10**(3 * millidx),1):0}{millnames[millidx]}'
    
    async def create_level_card(self, user: discord.Member, rank: int, exp: int):
        base_image = Image.open('./assets/level_template.png')
        profile = user.avatar.with_format('png')
        profile = BytesIO(await profile.read())
        profile = Image.open(profile)
        profile = profile.resize((189, 189), Image.Resampling.LANCZOS).convert('RGBA')

        draw = ImageDraw.Draw(base_image)
        name_font = ImageFont.truetype('./assets/fonts/Clockwise-Light.ttf', 38)
        other_font = ImageFont.truetype('./assets/fonts/Clockwise-Light.ttf', 32)
        base_image.paste(profile, (39, 46))

        #exp = exp.split(".")[0]

        draw.text((275, 46), f"{user.name}#{user.discriminator}", fill="#9A9BD5", font=name_font)
        draw.text((508, 122), f"# {rank}", fill="#A8A8C8", font=other_font)
        draw.text((508, 182), f"{exp}", fill="#A8A8C8", font=other_font)

        return base_image


    async def get_rank(self, user_id):
        if user_id in self.bot.rank_cache.keys():
            return self.bot.rank_cache[user_id]
        else:
            data = await self.bot.ranks.find(user_id)
            if not data: 
                data = self.template_db(user_id)
                self.bot.rank_cache[user_id] = data
                await self.bot.ranks.insert(data)
            return data

    async def update_rank(self, user_id, data):
        await self.bot.ranks.update(data)
        self.bot.rank_cache[user_id] = data
    
    @tasks.loop(seconds=60)
    async def update_level_config(self):
        config = await self.bot.level_config.get_all()
        for guild in config: self.bot.level_config_cache[guild['_id']] = guild

    @update_level_config.before_loop
    async def before_update_level_config(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_ready(self):
        config = await self.bot.level_config.get_all()
        for guild in config: self.bot.level_config_cache[guild['_id']] = guild
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild: return
        if message.author.id == self.bot.user.id: return

        if message.guild.id not in self.bot.level_config_cache.keys(): return
        guild_data = self.bot.level_config_cache[message.guild.id]
        if not guild_data:
            guild_data = await self.bot.level_config.find(message.guild.id)
            if guild_data == None:
                return

        if message.author.bot and message.interaction != None: 
            self.bot.dispatch("slash_command", message)
        elif not message.author.bot:
            self.bot.dispatch("update_xp", message)
        

    @commands.Cog.listener()
    async def on_update_xp(self, message):
        if message.author.id in self.bot.rank_in_progress.keys(): return
        user_data = await self.get_rank(message.author.id)
        exp = 1

        if user_data['last_updated'] != None:
            if (datetime.datetime.utcnow() - user_data['last_updated']).total_seconds() < 8:
                try:
                    self.bot.rank_in_progress.pop(message.author.id)
                except KeyError:
                    pass
                return        

        multiplier = self.bot.level_config_cache[message.guild.id]['multiplier']['global']

        user_data['xp'] += exp * multiplier
        user_data['last_updated'] = datetime.datetime.utcnow()
        await self.update_rank(message.author.id, user_data)

        try:
            self.bot.rank_in_progress.pop(message.author.id)
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_slash_command(self, message):
        if message.author.id in self.bot.rank_in_progress.keys(): return
        user = message.interaction.user
        user_data = await self.get_rank(user.id)

        if user_data['last_updated'] != None:

            if (datetime.datetime.utcnow() - user_data['last_updated']).total_seconds() < 8:
                try:
                    self.bot.rank_in_progress.pop(user.id)
                except KeyError:
                    pass
                return

        multiplier = self.bot.level_config_cache[message.guild.id]['multiplier']['global']

        user_data['xp'] += 1 * multiplier
        user_data['last_updated'] = datetime.datetime.utcnow()
        await self.update_rank(user.id, user_data)

        try:
            self.bot.rank_in_progress.pop(user.id)
        except KeyError:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        if guild.id in self.bot.level_config_cache.keys():
            guild_data = self.bot.level_config_cache[guild.id]
        else:
            guild_data = await self.bot.level_config.find(guild.id)
            if guild_data == None:
                return
        
        if guild_data['clear_on_leave'] == True:
            await self.bot.ranks.delete(member.id)
            try:
                self.bot.rank_cache.pop(member.id)
            except KeyError:
                pass


    @app_commands.command(name="rank", description="Get your or another users rank")
    @app_commands.describe(user="The user to get the rank of")
    @app_commands.checks.cooldown(1, 30)
    async def rank(self, interaction: Interaction, user: discord.Member = None):
        user = user if user else interaction.user
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Loading {user}'s rank...", color=0x2b2d31))

        if user.id in self.bot.rank_cache.keys():
            user_data = self.bot.rank_cache[user.id]
        else:
            user_data = await self.bot.ranks.find(user.id)
        
        if user_data is None: return await interaction.edit_original_response(embed=discord.Embed(description=f"User {user.mention} is not ranked yet", color=0x2b2d31))

        ranks = await self.bot.ranks.get_all()
        df = pd.DataFrame(ranks)
        df = df.sort_values(by="xp",ascending = False)
        df = df.reset_index(drop=True)
        rank = df.index[df['_id'] == user.id].tolist()[0] + 1

        if len(str(df['xp'][rank-1])) >=4:
            exp = await self.millify(df['xp'][rank-1])
        else:
            exp = df['xp'][rank-1]

        image = await self.create_level_card(user, rank, exp)

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            embed = discord.Embed(color=0x2b2d31)
            image_file = discord.File(fp=image_binary, filename=f'{user.id}_rank_cva.png')
            embed.set_image(url=f"attachment://{user.id}_rank_cva.png")
            await interaction.edit_original_response(embed=embed, attachments=[discord.File(fp=image_binary, filename=f'{user.id}_rank_cva.png')])

    @app_commands.command(name="leaderboard", description="Get the leaderboard")
    @app_commands.checks.cooldown(1, 30)
    async def leaderboard(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)
        data = await self.bot.ranks.get_all()
        df = pd.DataFrame(data)
        df = df.sort_values(by="xp",ascending = False)
        df = df.reset_index(drop=True)
        df = df.head(10)
        df = df.reset_index(drop=True)
        embed = discord.Embed(title=f"{interaction.guild.name} Leaderboard", color=0x2b2d31, description=f"{interaction.guild.name} Weekly Leaderboard\n\n")
        rank = df.index[df['_id'] == interaction.user.id].tolist()[0] + 1

        for i in range(10):
            try:
                user = self.bot.get_user(df['_id'][i])
                if user == None:
                    user = await self.bot.fetch_user(df['_id'][i])
                embed.description += f"**#{i+1}.** {user.mention}\n<:invis_space:1067363810077319270> Exp: `{df['xp'][i]}`\n\n"
            except KeyError:
                break

        embed.set_footer(text=f"Your rank: {rank}")
        embed.set_thumbnail(url=interaction.guild.icon.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(level(bot))
    await bot.add_cog(Level_BackEnd(bot))