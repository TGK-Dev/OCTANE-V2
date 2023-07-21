import asyncio
from typing import List
import discord
import math
import datetime
import random
import pytz
from discord import app_commands
from discord import Interaction
from discord.ext import commands, tasks
from utils.db import Document
from utils.transformer import TimeConverter, MutipleRole, DMCConverter
from utils.views.giveaway import Giveaway
from utils.converters import DMCConverter_Ctx
from utils.views.modal import General_Modal



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
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        member = payload.user
        guild = self.bot.get_guild(payload.guild_id)

        if member.bot: return
        if payload.guild_id is None: return
        if member.guild_id != 785839283847954433: return
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
            "dm_message": "Please dm Host to claim your prize!"
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

    @tasks.loop(seconds=10)
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
                    self.bot.dispatch("giveaway_end", giveaway)
                    self.giveaway_in_prosses.append(giveaway["_id"])
                    del self.backend.giveaways_cache[giveaway["_id"]]
            except TypeError:
                pass
        self.giveaway_task_progress = False

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_giveaway_end(self, giveaway: dict):
        guild: discord.Guild = self.bot.get_guild(giveaway["guild"])
        channel = guild.get_channel(giveaway["channel"])
        try:
            message = await channel.fetch_message(giveaway["_id"])
        except:
            await self.backend.giveaways.delete(giveaway["_id"])
            del self.backend.giveaways_cache[giveaway["_id"]]
            return
        
        if len(giveaway["entries"].keys()) == 0:
            embed = message.embeds[0]
            view = Giveaway()
            view.children[0].disabled = True
            await message.edit(embed=embed, view=view, content="**Giveaway has ended**")
            embed = discord.Embed(description="No one entered the giveaway", color=self.bot.default_color)
            await message.reply(embed=embed)
            await self.backend.giveaways.delete(giveaway["_id"])
            try:
                del self.backend.giveaways_cache[giveaway["_id"]]
            except:
                pass
            self.giveaway_in_prosses.remove(giveaway["_id"])
            return
        elif len(giveaway['entries'].keys()) < giveaway["winners"]:
            embed = message.embeds[0]
            view = Giveaway()
            view.children[0].disabled = True
            await message.edit(embed=embed, view=view, content="**Giveaway has ended**")
            embed = discord.Embed(description="Not enough people entered the giveaway", color=discord.Color.red())
            await message.reply(embed=embed)
            await self.backend.giveaways.delete(giveaway["_id"])
            try:
                del self.backend.giveaways_cache[giveaway["_id"]]
            except:
                pass
            self.giveaway_in_prosses.remove(giveaway["_id"])
            return
        
        enrtrys = []
        for key, value in giveaway["entries"].items():
            if int(key) in enrtrys:
                continue
            enrtrys.extend([int(key)] * value)
        
        winners = []
        while len(winners) != giveaway["winners"]:
            winner = random.choice(enrtrys)
            if winner in winners:
                continue
            winners.append(winner)

        embed: discord.Embed = message.embeds[0]
        if len(embed.fields) != 0:
            fields_names = [field.name for field in embed.fields]
            if "Winners" in fields_names:
                embed.set_field_at(fields_names.index("Winners"), name="Winners", value=", ".join([f"<@{winner}>" for winner in winners]), inline=False)
            else:
                embed.description += f"\nTotal Entries: {len(giveaway['entries'].keys())}"
                embed.add_field(name="Winners", value=", ".join([f"<@{winner}>" for winner in winners]), inline=False)
        else:
            embed.add_field(name="Winners", value=", ".join([f"<@{winner}>" for winner in winners]), inline=False)
        
        view = Giveaway()
        view.children[0].disabled = True
        await message.edit(embed=embed, view=view, content="**Giveaway has ended**")
        if giveaway["item"]:
            item = await self.bot.dank_items.find(giveaway["item"])
        else:
            item = None
        dm_embed = discord.Embed(title="You won a giveaway!", description=f"**Congratulations!** you won", color=self.bot.default_color)
        if giveaway["dank"]:
            if giveaway["item"]:
                dm_embed.description += f" {giveaway['prize']}x {item['_id']} in {guild.name}"
            else:
                dm_embed.description += f" ⏣ {giveaway['prize']:,} in {guild.name}"
        else:
            dm_embed.description += f" {giveaway['prize']} in {guild.name}"
        config = await self.backend.get_config(guild)
        if config["dm_message"]:
            dm_embed.description += f"\n{config['dm_message']}"
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Giveaway Link!", url=message.jump_url, style=discord.ButtonStyle.link))
        for winner in winners:
            winner = guild.get_member(winner)
            if winner is None: continue
            try:
                await winner.send(embed=dm_embed, view=link_view)
            except:
                pass
        embed = discord.Embed(title="Congratulations", color=self.bot.default_color, description="")
        if giveaway["dank"]:
            if giveaway["item"]:
                embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** {giveaway['prize']}x {giveaway['item']}\n"
            else:
                embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** ⏣ {giveaway['prize']:,}\n"
        else:
            embed.description += f"<a:tgk_blackCrown:1097514279973961770>  **Won:** {giveaway['prize']}\n"
        embed.set_footer(text="Make sure to claim your prize from claim channel!")
        win_message = await message.reply(embed=embed, content=",".join([f"<@{winner}>" for winner in winners]))
        host = guild.get_member(giveaway["host"])
        
        if giveaway['dank'] != False:
            try:
                for winner in winners:
                    await self.bot.create_payout(event="Giveaway", winner=winner, host=guild.get_member(giveaway['host']), prize=giveaway["prize"], message=win_message, item=item)    
            except:
                if host:
                    try:
                        await host.send(f"I was unable to create a payout for some/all winners of your giveaway at {message.jump_url}")
                    except discord.HTTPException:
                        pass

        if host: 
            host_dm = discord.Embed(title=f"Your Giveaway ", description="", color=self.bot.default_color)
            if giveaway["dank"]:
                if giveaway["item"]:
                    host_dm.title += f"{giveaway['prize']}x {giveaway['item']} has ended"
                else:
                    host_dm.title += f"⏣ {giveaway['prize']:,} has ended"
            else:
                host_dm.title += f"{giveaway['prize']} has ended"
        
            embed.description += f"Total entries: {len(giveaway['entries'].keys())}\n"
            embed.description += f"Total Winners: {len(winners)}\n"
            i = 1
            for winner in winners:
                winner = guild.get_member(winner)
                if winner is None: continue
                host_dm.description += f"> {i}. {winner.mention}\n"
                i += 1
            try:
                await host.send(embed=host_dm, view=link_view)
            except:
                pass

        giveaway['ended'] = True
        await self.backend.giveaways.update(giveaway)
        del self.backend.giveaways_cache[giveaway["_id"]]
        self.giveaway_in_prosses.remove(giveaway["_id"])
    
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
                return await interaction.followup.send("Invalid Prize!", ephemeral=True)
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
        embed.description += f"End Time: <t:{timnestamp}:R> (<t:{timnestamp}:T>)\n"
        embed.description += f"Winners: {winners}\n"
        embed.description += f"Host: {interaction.user.mention}\n"
        if donor:
            embed.description += f"Donor: {donor.mention}"
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
    
    @app_commands.command(name="reroll", description="Reroll a giveaway")
    @app_commands.describe(
        message="Message to accompany the reroll",
        winners="Numbers of winners to reroll"
    )
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
        else:
            return

    @app_commands.command(name="end", description="End a giveaway")
    @app_commands.describe(
        message="Message to accompany the end"
    )
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

async def setup(bot):
    await bot.add_cog(Level(bot))
    await bot.add_cog(Giveaways(bot))